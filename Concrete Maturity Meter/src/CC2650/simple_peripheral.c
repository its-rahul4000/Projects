/******************************************************************************
// ---- 60 Min interval Ble  with serial console and 2 hour Hold Logic ----

 @file  simple_peripheral.c

 @brief This file contains the Simple BLE Peripheral sample application for use
        with the CC2650 Bluetooth Low Energy Protocol Stack.
 *****************************************************************************/

/*********************************************************************
 * INCLUDES
 */
#include <string.h>
#include <stdbool.h>
#include <math.h>   //

#include <ti/sysbios/knl/Task.h>
#include <ti/sysbios/knl/Clock.h>
#include <ti/sysbios/knl/Semaphore.h>
#include <ti/sysbios/knl/Queue.h>

#include <ti/drivers/I2C.h>
#include <ti/drivers/SPI.h>
#include <ti/drivers/PIN.h>
#include <ti/mw/display/Display.h>

#include "hci_tl.h"
#include "gatt.h"
#include "linkdb.h"
#include "gapgattserver.h"
#include "gattservapp.h"
#include "devinfoservice.h"
#include "simple_gatt_profile.h"

#if defined(FEATURE_OAD) || defined(IMAGE_INVALIDATE)
#include "oad_target.h"
#include "oad.h"
#endif 

#include "peripheral.h"
#include "gapbondmgr.h"
#include "gap.h"

#include "osal_snv.h" 
#include "icall_apimsg.h"
#include "util.h"

#ifdef USE_RCOSC
#include "rcosc_calibration.h"
#endif 

#include "board_key.h"
#include "board.h"
#include "simple_peripheral.h"

#include <driverlib/sys_ctrl.h>

#if defined( USE_FPGA ) || defined( DEBUG_SW_TRACE )
#include <driverlib/ioc.h>
#endif 

/*********************************************************************
 * CONSTANTS & DEFINES
 */
// BLE connection parameters defining latency and timeout tolerances
#define DEFAULT_ADVERTISING_INTERVAL          800  // 800 * 0.625ms = 500ms
#define DEFAULT_DISCOVERABLE_MODE             GAP_ADTYPE_FLAGS_GENERAL
#define DEFAULT_DESIRED_MIN_CONN_INTERVAL     80
#define DEFAULT_DESIRED_MAX_CONN_INTERVAL     800
#define DEFAULT_DESIRED_SLAVE_LATENCY         0
#define DEFAULT_DESIRED_CONN_TIMEOUT          1000
#define DEFAULT_ENABLE_UPDATE_REQUEST         GAPROLE_LINK_PARAM_UPDATE_INITIATE_BOTH_PARAMS
#define DEFAULT_CONN_PAUSE_PERIPHERAL         6

// --- SENSOR TIMING (10 Minutes per sample) ---
// Base interval for taking temperature readings (in milliseconds)
#define SBP_PERIODIC_EVT_PERIOD               600000 

// --- FAST HARDWARE DIAGNOSTIC TIMING (5 Seconds) ---
// Interval for checking if I2C/SPI peripherals are physically connected
#define SBP_DIAGNOSTIC_PERIOD                 5000 

// --- BLE DUTY CYCLE TIMINGS ---
// Power-saving parameters: limits active BLE radio time
#define ADV_ON_DURATION                       12000   // 12 Seconds awake
#define ADV_OFF_DURATION                      300000  // 5 Minutes asleep

// RTOS Task configuration
#define SBP_TASK_PRIORITY                     1
#define SBP_TASK_STACK_SIZE                   1024 

// --- EVENT FLAGS ---
// Bitmask flags for RTOS event handling via semaphores
#define SBP_STATE_CHANGE_EVT                  0x0001
#define SBP_CHAR_CHANGE_EVT                   0x0002
#define SBP_PERIODIC_EVT                      0x0004
#define SBP_CONN_EVT_END_EVT                  0x0008
#define SBP_ADV_OFF_EVT                       0x0020  // Trigger sleep mode
#define SBP_ADV_ON_EVT                        0x0040  // Trigger wake mode
#define SBP_DIAGNOSTIC_EVT                    0x0080  // Instant wire-pull check
#define SBP_BTN_EVT                           0x0100  // Button 2 pressed

// --- INTERNAL MEMORY (SNV) IDs ---
// Non-volatile memory addresses used for power-loss recovery
#define SNV_ID_UPTIME                         0x80
#define SNV_ID_MATURITY                       0x82
#define SNV_ID_STRENGTH                       0x84    // SNV Slot for Strength
#define SNV_ID_SAMPLE_COUNT                   0x86    // SNV Slot for 10-min ticks
#define SNV_ID_TEMP_ACCUM                     0x88    // SNV Slot for temp sum

// --- EXTERNAL FLASH MEMORY BASE ---
// Starting address for data logging on the external SPI Flash chip
#define FLASH_ADDR_LOG_BASE                   0x000000 

// --- COMPRESSIVE STRENGTH CONSTANTS (S = A + B * ln(M)) ---
// Calibration constants for the Nurse-Saul logarithmic curve
#define STRENGTH_CONST_A                      -35.4926f   // Replace with your mix's A value
#define STRENGTH_CONST_B                      7.5004f   // Replace with your mix's B value

// --- OPTIMIZED FLASH STRUCTURE (EXACTLY 16 BYTES) ---
// Struct strictly padded to 16 bytes for aligned flash writes and reads
typedef struct {
    uint32_t minute;              // 4 Bytes: Stores the Hour
    float    cumulativeMaturity;  // 4 Bytes: Total Maturity Index
    float    compressiveStrength; // 4 Bytes: Estimated Strength
    uint8_t  padding[4];          // 4 Bytes: Padding to equal 16 Bytes (Perfect alignment)
} LogRecord_t;

// Standard application event header for queueing
typedef struct {
    appEvtHdr_t hdr; 
} sbpEvt_t;

/*********************************************************************
 * GLOBAL VARIABLES
 */
// Serial display handle for debugging
Display_Handle dispHandle = NULL;
// Handle for the temperature sensor bus
static I2C_Handle i2c;

// --- MATURITY & STRENGTH TRACKING VARIABLES ---
// Datum temp below which concrete stops curing
#define DATUM_TEMPERATURE -10.0f
// Sub-hour accumulation variables
static float    tempAccumulator    = 0.0f;
static uint8_t  sampleCount        = 0;
// Lifetime metrics
static uint32_t hoursUptime        = 0;       // Tracking Hours 
static float    cumulativeMaturity = 0.0f;
static float    compressiveStrength= 0.0f;    // Tracking Variable
// Fault tolerance: holds last valid reading in case I2C drops
static float    lastGoodTemp       = 25.0f;   // Fault Tolerance
static bool     extFlashDead       = false;   // Fault Tolerance

// --- 2-HOUR DEPLOYMENT HOLD COUNTER ---
// Delays sensor tracking logic during initial physical deployment
static uint8_t  deploymentHoldCounter = 0;

// Tracks current BLE connection profile state
static gaprole_States_t gapProfileState = GAPROLE_INIT; 

// --- SPI FLASH VARIABLES ---
// Hardware configurations for external storage
static SPI_Handle spiHandle = NULL;
static SPI_Params spiParams;
static PIN_Handle flashCsPinHandle;
static PIN_State  flashCsPinState;

// Define the Chip Select (CS) pin for the SPI interface
static PIN_Config flashCsPinTable[] = {
    Board_SPI_FLASH_CS | PIN_GPIO_OUTPUT_EN | PIN_GPIO_HIGH | PIN_PUSHPULL | PIN_DRVSTR_MIN,
    PIN_TERMINATE
};

// --- BUTTON PINS ---
// Hardware configurations for user input
static PIN_Handle buttonPinHandle;
static PIN_State buttonPinState;

// Button configuration with interrupt on falling edge (press)
static PIN_Config buttonPinTable[] = {
    Board_BTN2 | PIN_INPUT_EN | PIN_PULLUP | PIN_IRQ_NEGEDGE | PIN_HYSTERESIS,
    PIN_TERMINATE
};

/*********************************************************************
 * LOCAL VARIABLES
 */
// RTOS entity variables
static ICall_EntityID selfEntity;
static ICall_Semaphore sem;
// Timers defining app execution flow
static Clock_Struct periodicClock;
static Clock_Struct diagnosticClock;
static Clock_Struct advOffClock;
static Clock_Struct advOnClock;
static bool isBLEAdvertising = true;
// Queue for managing asynchronous events
static Queue_Struct appMsg;
static Queue_Handle appMsgQueue;
static uint16_t events;
Task_Struct sbpTask;
Char sbpTaskStack[SBP_TASK_STACK_SIZE];

// --- "Comp Strength" Device Name ---
// What shows up in the BLE Scanner
static uint8_t scanRspData[] = {
    0x0E, GAP_ADTYPE_LOCAL_NAME_COMPLETE,
    'C','o','m','p',' ','S','t','r','e','n','g','t','h'
};

// --- FIX: Restored ORIGINAL BLE Payload Structure so UTF-8 Text shows properly ---
// Pre-formatting a static string. Bytes 7-15 will be overwritten dynamically with live strength data
static uint8_t advertData[] = {
    0x02, GAP_ADTYPE_FLAGS, GAP_ADTYPE_FLAGS_GENERAL | GAP_ADTYPE_FLAGS_BREDR_NOT_SUPPORTED,
    0x10, GAP_ADTYPE_MANUFACTURER_SPECIFIC, 0x0D, 0x00, 
    '0','0','0','0','.','0','0','0','0',' ','M','P','a' 
};

// GATT profile device name
static uint8_t attDeviceName[GAP_DEVICE_NAME_LEN] = "Comp Strength";
static gattMsgEvent_t *pAttRsp = NULL;
static uint8_t rspTxRetry = 0;

/*********************************************************************
 * LOCAL FUNCTIONS
 */
// Forward declarations for organizational scope
static void SimpleBLEPeripheral_init( void );
static void SimpleBLEPeripheral_taskFxn(UArg a0, UArg a1);
static uint8_t SimpleBLEPeripheral_processStackMsg(ICall_Hdr *pMsg);
static uint8_t SimpleBLEPeripheral_processGATTMsg(gattMsgEvent_t *pMsg);
static void SimpleBLEPeripheral_processAppMsg(sbpEvt_t *pMsg);
static void SimpleBLEPeripheral_processStateChangeEvt(gaprole_States_t newState);
static void SimpleBLEPeripheral_processCharValueChangeEvt(uint8_t paramID);
static void SimpleBLEPeripheral_performPeriodicTask(void);
static void SimpleBLEPeripheral_performDiagnosticTask(void);
static void SimpleBLEPeripheral_clockHandler(UArg arg);
static void SimpleBLEPeripheral_sendAttRsp(void);
static void SimpleBLEPeripheral_freeAttRsp(uint8_t status);
static void SimpleBLEPeripheral_stateChangeCB(gaprole_States_t newState);

static void powerUpSpi(void);
static void powerDownSpi(void);
static void initExtFlash(void);
static void initSensor(void); 
static void Flash_WaitReady(void);
static void Flash_WriteEnable(void);
static void Flash_EraseSector(uint32_t addr);
static void Flash_WriteData(uint32_t addr, uint8_t *data, uint16_t len);
static void Flash_ReadData(uint32_t addr, uint8_t *data, uint16_t len);
static void buttonCallbackFxn(PIN_Handle handle, PIN_Id pinId);

#ifndef FEATURE_OAD_ONCHIP
static void SimpleBLEPeripheral_charValueChangeCB(uint8_t paramID);
#endif 

static void SimpleBLEPeripheral_enqueueMsg(uint8_t event, uint8_t state);

extern void AssertHandler(uint8 assertCause, uint8 assertSubcause);

// BLE Callback structures mapped to internal handlers
static gapRolesCBs_t SimpleBLEPeripheral_gapRoleCBs = { SimpleBLEPeripheral_stateChangeCB };
static gapBondCBs_t simpleBLEPeripheral_BondMgrCBs = { NULL, NULL };

#ifndef FEATURE_OAD_ONCHIP
static simpleProfileCBs_t SimpleBLEPeripheral_simpleProfileCBs = { SimpleBLEPeripheral_charValueChangeCB };
#endif 

/*********************************************************************
 * PUBLIC FUNCTIONS
 */
// RTOS entry point: constructs the main task thread
void SimpleBLEPeripheral_createTask(void)
{
    Task_Params taskParams;
    Task_Params_init(&taskParams);
    taskParams.stack = sbpTaskStack;
    taskParams.stackSize = SBP_TASK_STACK_SIZE;
    taskParams.priority = SBP_TASK_PRIORITY;
    Task_construct(&sbpTask, SimpleBLEPeripheral_taskFxn, &taskParams, NULL);
}

// --- I2C SENSOR DIAGNOSTIC FUNCTION ---
// Validates whether the temperature sensor is accessible on boot
static void initSensor(void) 
{
    I2C_Params i2cParams;
    I2C_Params_init(&i2cParams);
    i2cParams.bitRate = I2C_400kHz;
    i2c = I2C_open(Board_I2C, &i2cParams);

    if (i2c == NULL) 
    {
        Display_print0(dispHandle, 0, 0, "!!! CRITICAL ERROR: I2C DRIVER FAILED TO OPEN !!!");
        return;
    }

    // Ping the sensor with a dummy write to address 0x48 to test ack
    uint8_t txBuf[1] = {0x00};
    uint8_t rxBuf[2] = {0, 0}; 
    
    I2C_Transaction i2cTransaction;
    memset(&i2cTransaction, 0, sizeof(I2C_Transaction));
    i2cTransaction.slaveAddress = 0x48;
    i2cTransaction.writeBuf     = txBuf; 
    i2cTransaction.writeCount   = 1;
    i2cTransaction.readBuf      = rxBuf; 
    i2cTransaction.readCount    = 2;

    if (I2C_transfer(i2c, &i2cTransaction)) 
    {
        Display_print0(dispHandle, 0, 0, "--> Temp Sensor Connected Successfully.");
    } 
    else 
    {
        Display_print0(dispHandle, 0, 0, "!!! WARNING: TEMP SENSOR MISSING !!!");
    }
    
    I2C_close(i2c);
}

// --- SPI POWER WRAPPERS TO PREVENT GLITCHING ---
// Safely opens/closes the SPI driver to manage power consumption and avoid line contention
static void powerUpSpi(void)
{
    if (spiHandle == NULL) 
    {
        spiHandle = SPI_open(Board_SPI0, &spiParams);
    }
}

static void powerDownSpi(void)
{
    if (spiHandle != NULL) 
    {
        SPI_close(spiHandle);
        spiHandle = NULL;
    }
}

// --- SPI FLASH DRIVER FUNCTIONS ---
// Initializes the external SPI Flash chip and requests its JEDEC ID
static void initExtFlash(void) 
{
    flashCsPinHandle = PIN_open(&flashCsPinState, flashCsPinTable);
    SPI_Params_init(&spiParams);
    spiParams.bitRate     = 1000000;      
    spiParams.frameFormat = SPI_POL0_PHA0; 
    spiParams.mode        = SPI_MASTER;
    
    powerUpSpi();
    if (spiHandle != NULL) 
    {
        // JEDEC ID Command (0x9F) to verify device presence
        uint8_t txBuffer[4] = {0x9F, 0x00, 0x00, 0x00}; 
        uint8_t rxBuffer[4] = {0, 0, 0, 0};
        SPI_Transaction t = { .count = 4, .txBuf = txBuffer, .rxBuf = rxBuffer };

        PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 0); 
        SPI_transfer(spiHandle, &t);
        PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 1); 

        // 0xEF is the expected Manufacturer ID for Winbond chips
        if (rxBuffer[1] == 0xEF) 
        {
            Display_print0(dispHandle, 0, 0, "--> Ext Flash Memory Connected Successfully.");
            extFlashDead = false;
        } 
        else 
        {
            Display_print0(dispHandle, 0, 0, "!!! WARNING: EXT FLASH MISSING   !!!");
            extFlashDead = true;
        }
    }
    powerDownSpi();
}

// Blocks execution until the Flash chip finishes its internal write/erase cycle
static void Flash_WaitReady(void) 
{
    if (extFlashDead || spiHandle == NULL) return; 

    // Read Status Register-1 command (0x05)
    uint8_t tx[2] = {0x05, 0x00}; 
    uint8_t rx[2] = {0, 0};
    SPI_Transaction t = { .count = 2, .txBuf = tx, .rxBuf = rx };
    uint32_t timeoutCounter = 0;
    
    do 
    {
        rx[1] = 0xFF; 
        PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 0);
        SPI_transfer(spiHandle, &t);
        PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 1);
        
        // Check the BUSY bit (Bit 0). If 0, device is ready
        if ((rx[1] & 0x01) == 0) break; 
        
        // Context switch away to avoid locking up the RTOS while chip writes
        Task_sleep(1000); 
        timeoutCounter++;
        // Timeout to prevent infinite loops if chip physically breaks mid-write
        if (timeoutCounter > 500) 
        { 
            Display_print0(dispHandle, 0, 0, "!! DYNAMIC FAULT: SPI TIMEOUT !! Flash chip died.");
            extFlashDead = true; 
            break;
        }
    } while(1); 
}

// Sends Write Enable (WEL) command (0x06) before any erase/program operations
static void Flash_WriteEnable(void) 
{
    if (extFlashDead || spiHandle == NULL) return;
    
    uint8_t tx[1] = {0x06}; 
    SPI_Transaction t = { .count = 1, .txBuf = tx, .rxBuf = NULL };
    
    PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 0);
    SPI_transfer(spiHandle, &t);
    PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 1);
}

// Sends Sector Erase command (0x20) and targets a 24-bit address block (4KB chunk)
static void Flash_EraseSector(uint32_t addr) 
{
    if (extFlashDead || spiHandle == NULL) return;
    
    Flash_WriteEnable();
    
    uint8_t tx[4] = {0x20, (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF};
    SPI_Transaction t = { .count = 4, .txBuf = tx, .rxBuf = NULL };
    
    PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 0);
    SPI_transfer(spiHandle, &t);
    PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 1);
    
    Flash_WaitReady(); 
}

// Sends Page Program command (0x02) to write data bytes into memory arrays
static void Flash_WriteData(uint32_t addr, uint8_t *data, uint16_t len) 
{
    if (extFlashDead || spiHandle == NULL) return;
    
    Flash_WriteEnable();
    
    uint8_t tx[4] = {0x02, (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF};
    SPI_Transaction t1 = { .count = 4, .txBuf = tx, .rxBuf = NULL };
    SPI_Transaction t2 = { .count = len, .txBuf = data, .rxBuf = NULL };
    
    PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 0);
    SPI_transfer(spiHandle, &t1); // Send instruction + address
    SPI_transfer(spiHandle, &t2); // Send actual payload
    PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 1);
    
    Flash_WaitReady(); 
}

// Sends Read Data command (0x03) to fetch data from memory arrays
static void Flash_ReadData(uint32_t addr, uint8_t *data, uint16_t len) 
{
    if (extFlashDead || spiHandle == NULL) return;
    
    uint8_t tx[4] = {0x03, (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF};
    SPI_Transaction t1 = { .count = 4, .txBuf = tx, .rxBuf = NULL };
    SPI_Transaction t2 = { .count = len, .txBuf = NULL, .rxBuf = data };
    
    PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 0);
    SPI_transfer(spiHandle, &t1);
    SPI_transfer(spiHandle, &t2);
    PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 1);
}

// Hardware Interrupt Routine (HWI): Executed outside standard thread flow when Button 2 is pressed
static void buttonCallbackFxn(PIN_Handle handle, PIN_Id pinId)
{
    if (pinId == Board_BTN2 && !PIN_getInputValue(Board_BTN2))
    {
        events |= SBP_BTN_EVT;
        Semaphore_post(sem); // Wakens the task thread to process the event
    }
}

// Task Initialization Logic
static void SimpleBLEPeripheral_init(void)
{
    // Register the current thread with ICall to receive stack messages
    ICall_registerApp(&selfEntity, &sem);

#ifdef USE_RCOSC
    RCOSC_enableCalibration();
#endif 

    // Create RTOS queue to process asynchronous events safely
    appMsgQueue = Util_constructQueue(&appMsg);
    
    // Core Sensor Reading Clock (Every 10 Minutes)
    // Fires SBP_PERIODIC_EVT repeatedly to sample temp
    Util_constructClock(&periodicClock, SimpleBLEPeripheral_clockHandler,
                        SBP_PERIODIC_EVT_PERIOD, SBP_PERIODIC_EVT_PERIOD, true, SBP_PERIODIC_EVT);

    // Fast Hardware Diagnostic Clock (Every 5 Seconds)
    // Continuous polling for physical disconnections
    Util_constructClock(&diagnosticClock, SimpleBLEPeripheral_clockHandler,
                        SBP_DIAGNOSTIC_PERIOD, SBP_DIAGNOSTIC_PERIOD, true, SBP_DIAGNOSTIC_EVT);

    // BLE Sleep Control Clocks
    // Creates a duty cycle: toggling between wake (12s) and sleep (5m) to save power
    Util_constructClock(&advOffClock, SimpleBLEPeripheral_clockHandler,
                        ADV_ON_DURATION, 0, false, SBP_ADV_OFF_EVT);
    Util_constructClock(&advOnClock, SimpleBLEPeripheral_clockHandler,
                        ADV_OFF_DURATION, 0, false, SBP_ADV_ON_EVT);

    dispHandle = Display_open(Display_Type_UART, NULL);
    
    buttonPinHandle = PIN_open(&buttonPinState, buttonPinTable);
    if (buttonPinHandle != NULL)
    {
        PIN_registerIntCb(buttonPinHandle, &buttonCallbackFxn);
    }
    
    // Hardware Diagnostics on Boot
    initExtFlash(); 
    initSensor();

    GAP_SetParamValue(TGAP_CONN_PAUSE_PERIPHERAL, DEFAULT_CONN_PAUSE_PERIPHERAL);

    // --- FAULT-TOLERANT MEMORY RESTORE & HARDWARE RESET ---
    // Distinguish between an intentional Reset Button press vs. a low-voltage battery drop (brownout)
    uint32_t resetSource = SysCtrlResetSourceGet();

    // If reset was manual (Button press or flashing tool): Wipe all historical data and start fresh
    if (resetSource == RSTSRC_PIN_RESET) 
    {
        hoursUptime = 0;
        cumulativeMaturity = 0.0f;
        compressiveStrength = 0.0f;
        sampleCount = 0;           
        tempAccumulator = 0.0f;    
        
        // --- RULE 3: Set deployment hold for 12 ticks (120 minutes) ---
        // Prevents processing ambient temperature while devices are driven to the deployment site
        deploymentHoldCounter = 12;
        
        // Zero out the internal SNV memory registers
        osal_snv_write(SNV_ID_UPTIME, sizeof(uint32_t), &hoursUptime);
        osal_snv_write(SNV_ID_MATURITY, sizeof(float), &cumulativeMaturity);
        osal_snv_write(SNV_ID_STRENGTH, sizeof(float), &compressiveStrength);
        osal_snv_write(SNV_ID_SAMPLE_COUNT, sizeof(uint8_t), &sampleCount); 
        osal_snv_write(SNV_ID_TEMP_ACCUM, sizeof(float), &tempAccumulator); 

        // Erase sector 0 of the external flash
        if (!extFlashDead) 
        {
            powerUpSpi();
            Flash_EraseSector(FLASH_ADDR_LOG_BASE); // Wipe Sector 0 to clear history
            powerDownSpi();
        }
        Display_print0(dispHandle, 0, 0, "SYSTEM RESET: INTERNAL MEM & EXT MEM HISTORY WIPED.");
        // --- RULE 3: PRINT DEPLOYMENT HOLD MESSAGE ONCE ---
        Display_print0(dispHandle, 0, 0, ">> 2 HOUR DEPLOYMENT HOLD IN PROGRESS...");
    } 
    else 
    {
        // POWER LOSS/CORRUPTION RECOVERY (Pulls ONLY from SNV)
        // If the device lost power due to a drained battery, retrieve the last known values
        uint8_t readTime = osal_snv_read(SNV_ID_UPTIME, sizeof(uint32_t), &hoursUptime);
        uint8_t readMat  = osal_snv_read(SNV_ID_MATURITY, sizeof(float), &cumulativeMaturity);
        uint8_t readStr  = osal_snv_read(SNV_ID_STRENGTH, sizeof(float), &compressiveStrength);
        
        uint8_t readSamp = osal_snv_read(SNV_ID_SAMPLE_COUNT, sizeof(uint8_t), &sampleCount);
        uint8_t readAcc  = osal_snv_read(SNV_ID_TEMP_ACCUM, sizeof(float), &tempAccumulator);
        
        // Safety check: if memory is corrupt or missing, restart the current hour at 0 mins
        // Ensures `sampleCount` bounds aren't violated, preventing infinite math errors
        if (readSamp != SUCCESS || readAcc != SUCCESS || sampleCount >= 6) 
        {
            sampleCount = 0;
            tempAccumulator = 0.0f;
        }
        
        // Validate maturity bounds
        if (readTime == SUCCESS && readMat == SUCCESS && cumulativeMaturity >= 0.0f && cumulativeMaturity <= 1000000.0f) 
        {
            // Fail-safe calculation: if strength value is lost but maturity exists, recalculate using logarithmic formula
            if (readStr != SUCCESS && cumulativeMaturity > 0.0f) {
                compressiveStrength = STRENGTH_CONST_A + STRENGTH_CONST_B * logf(cumulativeMaturity);
                if (compressiveStrength < 0.0f) compressiveStrength = 0.0f;
            }

            // Deconstruct float for UART printing (CC2650 printf lacks robust %f handling)
            int mWhole = (int)cumulativeMaturity;
            int mFrac  = (int)((cumulativeMaturity - mWhole) * 10000); 
            if (mFrac < 0) mFrac = -mFrac;

            int sWhole = (int)compressiveStrength;
            int sFrac  = (int)((compressiveStrength - sWhole) * 10000); 
            if (sFrac < 0) sFrac = -sFrac;
            
            Display_print0(dispHandle, 0, 0, "--> Successfully recovered Total State from Internal SNV:");
            Display_print3(dispHandle, 0, 0, "    Restored Hour: %d | Mat: %d.%04d", hoursUptime, mWhole, mFrac);
            Display_print2(dispHandle, 0, 0, "                       | Str: %d.%04d", sWhole, sFrac);
            Display_print2(dispHandle, 0, 0, "    Resuming at Sample %d/6 with Temp Sum: %d", sampleCount, (int)tempAccumulator);
            
            if (hoursUptime == 0 && sampleCount == 0) 
            {
                // If power died exactly during the hold, restart the hold automatically
                deploymentHoldCounter = 12;
                Display_print0(dispHandle, 0, 0, ">> 2 HOUR DEPLOYMENT HOLD RESTARTED...");
            } 
            else 
            {
                // Otherwise, bypass hold to not lose any data
                deploymentHoldCounter = 0; 
            }
        } 
        else 
        {
            // Complete memory wipe fallback (Catastrophic SNV failure)
            hoursUptime = 0; 
            cumulativeMaturity = 0.0f;
            compressiveStrength = 0.0f;
            sampleCount = 0;
            tempAccumulator = 0.0f;
            
            // --- RULE 3: Start hold if SNV was completely empty
            deploymentHoldCounter = 12;
            Display_print0(dispHandle, 0, 0, "--> SNV Empty. Starting Fresh at Hour 0.");
            Display_print0(dispHandle, 0, 0, ">> 2 HOUR DEPLOYMENT HOLD IN PROGRESS...");
        }
    }
    
    // Format the initial BLE payload ONLY with Compressive Strength
    // Converts float strength value into ASCII characters for direct injection into BLE advertisement packet
    int strWhole = (int)compressiveStrength;
    int strFrac  = (int)((compressiveStrength - strWhole) * 10000); 
    if (strFrac < 0) strFrac = -strFrac;
    if (strWhole < 0) strWhole = 0; // Prevent negative formatting map
    
    // Manual integer-to-char mapping for the broadcast packet
    advertData[7]  = '0' + (strWhole / 1000) % 10;
    advertData[8]  = '0' + (strWhole / 100) % 10;
    advertData[9]  = '0' + (strWhole / 10) % 10;
    advertData[10] = '0' + (strWhole % 10);
    
    advertData[12] = '0' + (strFrac / 1000) % 10;
    advertData[13] = '0' + (strFrac / 100) % 10;
    advertData[14] = '0' + (strFrac / 10) % 10;
    advertData[15] = '0' + (strFrac % 10);

    // Initial configuration of BLE GAP Profile Parameters
    {
        uint8_t initialAdvertEnable = TRUE;
        uint16_t advertOffTime = 0;
        uint8_t enableUpdateRequest = DEFAULT_ENABLE_UPDATE_REQUEST;
        uint16_t desiredMinInterval = DEFAULT_DESIRED_MIN_CONN_INTERVAL;
        uint16_t desiredMaxInterval = DEFAULT_DESIRED_MAX_CONN_INTERVAL;
        uint16_t desiredSlaveLatency = DEFAULT_DESIRED_SLAVE_LATENCY;
        uint16_t desiredConnTimeout = DEFAULT_DESIRED_CONN_TIMEOUT;

        GAPRole_SetParameter(GAPROLE_ADVERT_ENABLED, sizeof(uint8_t), &initialAdvertEnable);
        
        uint8_t advType = GAP_ADTYPE_ADV_SCAN_IND;
        GAPRole_SetParameter(GAPROLE_ADV_EVENT_TYPE, sizeof(uint8_t), &advType);
        
        GAPRole_SetParameter(GAPROLE_ADVERT_OFF_TIME, sizeof(uint16_t), &advertOffTime);
        GAPRole_SetParameter(GAPROLE_SCAN_RSP_DATA, sizeof(scanRspData), scanRspData);
        GAPRole_SetParameter(GAPROLE_ADVERT_DATA, sizeof(advertData), advertData);
        GAPRole_SetParameter(GAPROLE_PARAM_UPDATE_ENABLE, sizeof(uint8_t), &enableUpdateRequest);
        GAPRole_SetParameter(GAPROLE_MIN_CONN_INTERVAL, sizeof(uint16_t), &desiredMinInterval);
        GAPRole_SetParameter(GAPROLE_MAX_CONN_INTERVAL, sizeof(uint16_t), &desiredMaxInterval);
        GAPRole_SetParameter(GAPROLE_SLAVE_LATENCY, sizeof(uint16_t), &desiredSlaveLatency);
        GAPRole_SetParameter(GAPROLE_TIMEOUT_MULTIPLIER, sizeof(uint16_t), &desiredConnTimeout);
    }

    GGS_SetParameter(GGS_DEVICE_NAME_ATT, GAP_DEVICE_NAME_LEN, attDeviceName);
    
    // Setting advertising interval rates
    {
        uint16_t advInt = DEFAULT_ADVERTISING_INTERVAL;
        GAP_SetParamValue(TGAP_LIM_DISC_ADV_INT_MIN, advInt);
        GAP_SetParamValue(TGAP_LIM_DISC_ADV_INT_MAX, advInt);
        GAP_SetParamValue(TGAP_GEN_DISC_ADV_INT_MIN, advInt);
        GAP_SetParamValue(TGAP_GEN_DISC_ADV_INT_MAX, advInt);
    }

    // GAP Bond Manager setup for security and pairing
    {
        uint32_t passkey = 0;
        uint8_t pairMode = GAPBOND_PAIRING_MODE_WAIT_FOR_REQ;
        uint8_t mitm = TRUE;
        uint8_t ioCap = GAPBOND_IO_CAP_DISPLAY_ONLY;
        uint8_t bonding = TRUE;
        
        GAPBondMgr_SetParameter(GAPBOND_DEFAULT_PASSCODE, sizeof(uint32_t), &passkey);
        GAPBondMgr_SetParameter(GAPBOND_PAIRING_MODE, sizeof(uint8_t), &pairMode);
        GAPBondMgr_SetParameter(GAPBOND_MITM_PROTECTION, sizeof(uint8_t), &mitm);
        GAPBondMgr_SetParameter(GAPBOND_IO_CAPABILITIES, sizeof(uint8_t), &ioCap);
        GAPBondMgr_SetParameter(GAPBOND_BONDING_ENABLED, sizeof(uint8_t), &bonding);
    }

    // Adding BLE Services to the stack
    GGS_AddService(GATT_ALL_SERVICES);
    GATTServApp_AddService(GATT_ALL_SERVICES);
    DevInfo_AddService();

#ifndef FEATURE_OAD_ONCHIP
    SimpleProfile_AddService(GATT_ALL_SERVICES);
    SimpleProfile_RegisterAppCBs(&SimpleBLEPeripheral_simpleProfileCBs);
#endif 

    // Register Callbacks and start up the BLE subsystem
    VOID GAPRole_StartDevice(&SimpleBLEPeripheral_gapRoleCBs);
    VOID GAPBondMgr_Register(&simpleBLEPeripheral_BondMgrCBs);
    GAP_RegisterForMsgs(selfEntity);
    GATT_RegisterForMsgs(selfEntity);
    HCI_LE_ReadMaxDataLenCmd();

    // Advertising defaults to ON during init, start the countdown to turn it OFF
    // This kicks off the duty-cycle timer
    Util_startClock(&advOffClock);
}

// RTOS Infinite Loop Thread
static void SimpleBLEPeripheral_taskFxn(UArg a0, UArg a1)
{
    SimpleBLEPeripheral_init();
    
    for (;;)
    {
        // OS will automatically put the chip into ultra-low-power sleep during this wait
        // Thread blocks here until an event flag wakes it up via semaphore
        ICall_Errno errno = ICall_wait(ICALL_TIMEOUT_FOREVER);
        
        if (errno == ICALL_ERRNO_SUCCESS)
        {
            ICall_EntityID dest;
            ICall_ServiceEnum src;
            ICall_HciExtEvt *pMsg = NULL;

            // Fetch and process messages pushed from the BLE Protocol Stack
            if (ICall_fetchServiceMsg(&src, &dest, (void **)&pMsg) == ICALL_ERRNO_SUCCESS)
            {
                uint8 safeToDealloc = TRUE;
                
                if ((src == ICALL_SERVICE_CLASS_BLE) && (dest == selfEntity))
                {
                    ICall_Stack_Event *pEvt = (ICall_Stack_Event *)pMsg;
                    if (pEvt->signature == 0xffff) 
                    {
                        if (pEvt->event_flag & SBP_CONN_EVT_END_EVT) 
                        { 
                            SimpleBLEPeripheral_sendAttRsp(); 
                        }
                    } 
                    else 
                    {
                        safeToDealloc = SimpleBLEPeripheral_processStackMsg((ICall_Hdr *)pMsg);
                    }
                }
                
                if (pMsg && safeToDealloc) 
                { 
                    ICall_freeMsg(pMsg); 
                }
            }

            // Process internal application messages
            while (!Queue_empty(appMsgQueue))
            {
                sbpEvt_t *pMsg = (sbpEvt_t *)Util_dequeueMsg(appMsgQueue);
                if (pMsg) 
                {
                    SimpleBLEPeripheral_processAppMsg(pMsg);
                    ICall_free(pMsg);
                }
            }
        }

        // --- BLE SLEEP TIMERS HANDLING ---
        // Puts the BLE radio to sleep to conserve battery for 5 minutes
        if (events & SBP_ADV_OFF_EVT)
        {
            events &= ~SBP_ADV_OFF_EVT;
            isBLEAdvertising = false;
            
            uint8_t advertEnable = FALSE;
            GAPRole_SetParameter(GAPROLE_ADVERT_ENABLED, sizeof(uint8_t), &advertEnable);
            
            Display_print0(dispHandle, 0, 0, ">> BLE is Sleeping"); 
            
            // Start the 5-min sleep countdown to wake up again
            Util_startClock(&advOnClock);
        }

        // Wakes the BLE radio up to broadcast for 12 seconds
        if (events & SBP_ADV_ON_EVT)
        {
            events &= ~SBP_ADV_ON_EVT;
            isBLEAdvertising = true;
            
            uint8_t advertEnable = TRUE;
            GAPRole_SetParameter(GAPROLE_ADVERT_ENABLED, sizeof(uint8_t), &advertEnable);
            Display_print0(dispHandle, 0, 0, ">> BLE is Advertising"); 
            
            // Start the 12-sec active countdown to sleep again
            Util_startClock(&advOffClock);
        }

        // --- INSTANT HARDWARE DIAGNOSTIC TASK ---
        // Runs every 5 seconds to test sensor/flash ping and detect disconnections
        if (events & SBP_DIAGNOSTIC_EVT)
        {
            events &= ~SBP_DIAGNOSTIC_EVT;
            Util_startClock(&diagnosticClock);
            SimpleBLEPeripheral_performDiagnosticTask();
        }

        // --- SENSOR PERIODIC TASK (10 Minutes) ---
        // Takes temperature readings, does calculation, stores data
        if (events & SBP_PERIODIC_EVT)
        {
            events &= ~SBP_PERIODIC_EVT;
            Util_startClock(&periodicClock);
            SimpleBLEPeripheral_performPeriodicTask();
        }

        // --- BUTTON 2 EVENT TASK ---
        // Serial printout of all data logged onto the external SPI Flash chip
        if (events & SBP_BTN_EVT)
        {
            events &= ~SBP_BTN_EVT;
            
            Display_print0(dispHandle, 0, 0, "=====================================================");
            Display_print0(dispHandle, 0, 0, "             External flash Log Dump                 ");
            Display_print0(dispHandle, 0, 0, "=====================================================");
            
            if (extFlashDead || hoursUptime == 0)
            {
                Display_print0(dispHandle, 0, 0, "        [ No External Log History Available ]        ");
            }
            else
            {
                Display_print0(dispHandle, 0, 0, " Hours   |    Maturity Index   |    Comp Strength    ");
                Display_print0(dispHandle, 0, 0, "-----------------------------------------------------");
                
                powerUpSpi();
                
                // Iterate through every recorded hour and read its 16-byte struct chunk
                for (uint32_t i = 1; i <= hoursUptime; i++)
                {
                    LogRecord_t rec;
                    uint32_t readAddr = FLASH_ADDR_LOG_BASE + ((i - 1) * sizeof(LogRecord_t));
                    Flash_ReadData(readAddr, (uint8_t*)&rec, sizeof(LogRecord_t));
                    
                    int mWhole = (int)rec.cumulativeMaturity;
                    int mFrac  = (int)((rec.cumulativeMaturity - mWhole) * 10000);
                    if (mFrac < 0) mFrac = -mFrac;
                    
                    int sWhole = (int)rec.compressiveStrength;
                    int sFrac  = (int)((rec.compressiveStrength - sWhole) * 10000);
                    if (sFrac < 0) sFrac = -sFrac;
                    
                    Display_print5(dispHandle, 0, 0, "  %04d   |   %04d.%04d Deg-Hr |    %04d.%04d MPa", 
                            rec.minute, mWhole, mFrac, sWhole, sFrac);
                }
                
                powerDownSpi();
            }
            Display_print0(dispHandle, 0, 0, "=====================================================");
        }
    }
}

// Stack message handler abstraction
static uint8_t SimpleBLEPeripheral_processStackMsg(ICall_Hdr *pMsg)
{
    uint8_t safeToDealloc = TRUE;
    
    switch (pMsg->event)
    {
        case GATT_MSG_EVENT:
            safeToDealloc = SimpleBLEPeripheral_processGATTMsg((gattMsgEvent_t *)pMsg);
            break;
            
        case HCI_GAP_EVENT_EVENT:
        {
            switch(pMsg->status) 
            {
                case HCI_COMMAND_COMPLETE_EVENT_CODE: 
                    break;
                case HCI_BLE_HARDWARE_ERROR_EVENT_CODE: 
                    AssertHandler(HAL_ASSERT_CAUSE_HARDWARE_ERROR,0); 
                    break;
                default: 
                    break;
            }
        }
        break;
        
        default: 
            break;
    }
    return (safeToDealloc);
}

// Routes GATT messages depending on BLE state
static uint8_t SimpleBLEPeripheral_processGATTMsg(gattMsgEvent_t *pMsg)
{
    if (pMsg->hdr.status == blePending) 
    {
        if (HCI_EXT_ConnEventNoticeCmd(pMsg->connHandle, selfEntity, SBP_CONN_EVT_END_EVT) == SUCCESS) 
        {
            SimpleBLEPeripheral_freeAttRsp(FAILURE);
            pAttRsp = pMsg;
            return (FALSE);
        }
    }
    GATT_bm_free(&pMsg->msg, pMsg->method);
    return (TRUE);
}

// Flushes the queued ATT Response
static void SimpleBLEPeripheral_sendAttRsp(void)
{
    if (pAttRsp != NULL) 
    {
        uint8_t status;
        rspTxRetry++;
        status = GATT_SendRsp(pAttRsp->connHandle, pAttRsp->method, &(pAttRsp->msg));
        
        if ((status != blePending) && (status != MSG_BUFFER_NOT_AVAIL)) 
        {
            HCI_EXT_ConnEventNoticeCmd(pAttRsp->connHandle, selfEntity, 0);
            SimpleBLEPeripheral_freeAttRsp(status);
        }
    }
}

// Safely deallocates the ATT Response pointer
static void SimpleBLEPeripheral_freeAttRsp(uint8_t status)
{
    if (pAttRsp != NULL) 
    {
        if (status != SUCCESS) 
        { 
            GATT_bm_free(&pAttRsp->msg, pAttRsp->method); 
        }
        
        ICall_freeMsg(pAttRsp);
        pAttRsp = NULL;
        rspTxRetry = 0;
    }
}

// Route internal queued messages
static void SimpleBLEPeripheral_processAppMsg(sbpEvt_t *pMsg)
{
    switch (pMsg->hdr.event) 
    {
        case SBP_STATE_CHANGE_EVT: 
            SimpleBLEPeripheral_processStateChangeEvt((gaprole_States_t)pMsg->hdr.state); 
            break;
        case SBP_CHAR_CHANGE_EVT: 
            SimpleBLEPeripheral_processCharValueChangeEvt(pMsg->hdr.state); 
            break;
        default: 
            break;
    }
}

// Enqueue state change events from the GAP profile
static void SimpleBLEPeripheral_stateChangeCB(gaprole_States_t newState) 
{ 
    SimpleBLEPeripheral_enqueueMsg(SBP_STATE_CHANGE_EVT, newState); 
}

// Handle transition between Advertising, Connected, and Waiting states
static void SimpleBLEPeripheral_processStateChangeEvt(gaprole_States_t newState)
{
    gapProfileState = newState;

    switch ( newState ) 
    {
        case GAPROLE_STARTED:
        {
            // Set the system ID based on hardware BD Address
            uint8_t ownAddress[B_ADDR_LEN]; 
            uint8_t systemId[DEVINFO_SYSTEM_ID_LEN];
            
            GAPRole_GetParameter(GAPROLE_BD_ADDR, ownAddress);
            systemId[0] = ownAddress[0]; 
            systemId[1] = ownAddress[1]; 
            systemId[2] = ownAddress[2];
            systemId[4] = 0x00; 
            systemId[3] = 0x00; 
            systemId[7] = ownAddress[5];
            systemId[6] = ownAddress[4]; 
            systemId[5] = ownAddress[3];
            
            DevInfo_SetParameter(DEVINFO_SYSTEM_ID, DEVINFO_SYSTEM_ID_LEN, systemId);
        }
        break;
        
        case GAPROLE_ADVERTISING: 
            break;
            
        case GAPROLE_CONNECTED: 
            break;
            
        case GAPROLE_CONNECTED_ADV: 
            break;
            
        case GAPROLE_WAITING:
        {
            // Re-enable advertising using our sleep tracker state if connection closes
            uint8_t advertReEnable = isBLEAdvertising ? TRUE : FALSE;
            SimpleBLEPeripheral_freeAttRsp(bleNotConnected);
            GAPRole_SetParameter(GAPROLE_ADVERT_ENABLED, sizeof(uint8_t), &advertReEnable);
        }
        break;
        
        case GAPROLE_WAITING_AFTER_TIMEOUT: 
            SimpleBLEPeripheral_freeAttRsp(bleNotConnected); 
            break;
        
        case GAPROLE_ERROR: 
            break;
            
        default: 
            break;
    }
}

#ifndef FEATURE_OAD_ONCHIP
static void SimpleBLEPeripheral_charValueChangeCB(uint8_t paramID) 
{ 
    SimpleBLEPeripheral_enqueueMsg(SBP_CHAR_CHANGE_EVT, paramID); 
}
#endif 

static void SimpleBLEPeripheral_processCharValueChangeEvt(uint8_t paramID)
{
#ifndef FEATURE_OAD_ONCHIP
    // No characteristic writing required.
#endif 
}

// Physical Hardware Watchdog logic
static void SimpleBLEPeripheral_performDiagnosticTask(void)
{
    // 1. SPI Hot-Swap Check
    // Probes the Flash chip to see if the physical pins disconnected/reconnected
    uint8_t testTx[4] = {0x9F, 0, 0, 0};
    uint8_t testRx[4] = {0, 0, 0, 0};
    SPI_Transaction tTest = { .count = 4, .txBuf = testTx, .rxBuf = testRx };
    
    powerUpSpi();
    if (spiHandle != NULL) 
    {
        PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 0); 
        SPI_transfer(spiHandle, &tTest);
        PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 1); 

        if (!extFlashDead) 
        {
            // If the chip was alive but stopped returning its JEDEC ID
            if (testRx[1] != 0xEF) 
            { 
                Display_print0(dispHandle, 0, 0, "--> !! EXT FLASH DISCONNECTED !!");
                extFlashDead = true;
            }
        } 
        else 
        {
            // Recovered: if the chip previously died but now responds
            if (testRx[1] == 0xEF) 
            {
                Display_print0(dispHandle, 0, 0, "--> EXT FLASH RECONNECTED ! RESUMING LOG SYNC.");
                extFlashDead = false;
            }
        }
    }
    powerDownSpi();

    // 2. I2C Temp Sensor Check
    // Probes the temp sensor address without requesting a payload
    I2C_Params i2cParams;
    I2C_Params_init(&i2cParams);
    i2cParams.bitRate = I2C_400kHz;
    I2C_Handle tempI2c = I2C_open(Board_I2C, &i2cParams);

    if (tempI2c != NULL) 
    {
        uint8_t txBuf[1] = {0x00};
        uint8_t rxBuf[2] = {0, 0}; 
        
        I2C_Transaction i2cTransaction;
        memset(&i2cTransaction, 0, sizeof(I2C_Transaction));
        i2cTransaction.slaveAddress = 0x48;
        i2cTransaction.writeBuf     = txBuf; 
        i2cTransaction.writeCount   = 1;
        i2cTransaction.readBuf      = rxBuf; 
        i2cTransaction.readCount    = 2;

        static bool i2cDead = false; 
        if (!I2C_transfer(tempI2c, &i2cTransaction))
        {
            if (!i2cDead)
            {
                Display_print0(dispHandle, 0, 0, "--> !! TEMP SENSOR DISCONNECTED   !!");
                i2cDead = true;
            }
        } 
        else 
        {
            if (i2cDead)
            {
                Display_print0(dispHandle, 0, 0, "--> TEMP SENSOR RECONNECTED.");
                i2cDead = false;
            }
        }
        I2C_close(tempI2c); 
    }
}

// Core business logic: Math, Memory Storage, and BLE updates
static void SimpleBLEPeripheral_performPeriodicTask(void)
{
    // --- RULE 3: 2-HOUR DEPLOYMENT HOLD ---
    if (deploymentHoldCounter > 0)
    {
        deploymentHoldCounter--;
        return; // Silently skip taking readings until 120 minutes is reached
    }

    // Open connection to I2C Temp sensor 
    I2C_Params i2cParams;
    I2C_Params_init(&i2cParams);
    i2cParams.bitRate = I2C_400kHz;
    i2c = I2C_open(Board_I2C, &i2cParams);

    uint8_t txBuf[1] = {0x00};
    uint8_t rxBuf[2] = {0, 0}; 
    
    I2C_Transaction i2cTransaction;
    memset(&i2cTransaction, 0, sizeof(I2C_Transaction));
    i2cTransaction.slaveAddress = 0x48;
    i2cTransaction.writeBuf     = txBuf; 
    i2cTransaction.writeCount   = 1;
    i2cTransaction.readBuf      = rxBuf; 
    i2cTransaction.readCount    = 2;

    float currentTemp;

    // Execute I2C reading
    if (i2c != NULL && I2C_transfer(i2c, &i2cTransaction))
    {
        I2C_close(i2c); 
        // Process raw byte data from standard I2C temp sensor (e.g., TMP102)
        int16_t rawTemp = (rxBuf[0] << 4) | (rxBuf[1] >> 4);
        
        // Handle negative temperatures (Two's complement expansion)
        if (rawTemp & 0x0800) 
        {
            rawTemp |= 0xF000;
        }
        
        currentTemp = rawTemp * 0.0625f;
        lastGoodTemp = currentTemp; // Cache successful reading
    }
    else
    {
        // Fault-tolerance: if reading fails, use the last known good temp
        if(i2c != NULL) 
        {
            I2C_close(i2c);
        }
        currentTemp = lastGoodTemp; 
    }

    tempAccumulator += currentTemp;
    sampleCount++;
    
    // Save sub-hour state to SNV every 10 minutes 
    // Prevents losing sub-hour fractional data in a brownout
    osal_snv_write(SNV_ID_SAMPLE_COUNT, sizeof(uint8_t), &sampleCount);
    osal_snv_write(SNV_ID_TEMP_ACCUM, sizeof(float), &tempAccumulator);
    
    int cWhole = (int)currentTemp;
    int cFrac  = (int)((currentTemp - cWhole) * 100); 
    
    if (cFrac < 0) 
    {
        cFrac = -cFrac;
    }
    
    Display_print3(dispHandle, 0, 0, "  [Sample %d/6] Current Sample Temp      : %d.%02d C", sampleCount, cWhole, cFrac);
    
    // Once 6 samples (60 mins) are taken, process the hourly math
    if (sampleCount >= 6) 
    {
        hoursUptime++;
        float averageTemp = tempAccumulator / 6.0f;
        float previousMaturity = cumulativeMaturity;
        float newMaturitySlice = 0.0f;

        // Nurse-Saul Maturity calculation logic: 
        // Index is only accumulated if temp is above the defined datum threshold
        if (averageTemp > DATUM_TEMPERATURE) 
        {
            float timeStepHours = 1.0f; 
            newMaturitySlice = (averageTemp - DATUM_TEMPERATURE) * timeStepHours;
            cumulativeMaturity = previousMaturity + newMaturitySlice;
        }

        // Convert Maturity to Compressive Strength using calibrated curve
        if (cumulativeMaturity > 0.0f) 
        {
            compressiveStrength = STRENGTH_CONST_A + STRENGTH_CONST_B * logf(cumulativeMaturity);
            if (compressiveStrength < 0.0f) compressiveStrength = 0.0f; // Cannot have negative physical strength
        }
        else 
        {
            compressiveStrength = 0.0f;
        }

        // Save hourly aggregated data to the TI internal memory
        osal_snv_write(SNV_ID_UPTIME, sizeof(uint32_t), &hoursUptime);
        osal_snv_write(SNV_ID_MATURITY, sizeof(float), &cumulativeMaturity);
        osal_snv_write(SNV_ID_STRENGTH, sizeof(float), &compressiveStrength);

        // Save hourly aggregated data to the external SPI memory
        if (!extFlashDead) 
        {
            LogRecord_t rec;
            memset(&rec, 0, sizeof(LogRecord_t)); 
            
            rec.minute = hoursUptime; 
            rec.cumulativeMaturity = cumulativeMaturity;
            rec.compressiveStrength = compressiveStrength; 
            
            powerUpSpi(); 
            
            // Calculate memory mapped address (each struct log is strictly 16 bytes)
            uint32_t logAddress = FLASH_ADDR_LOG_BASE + ((hoursUptime - 1) * sizeof(LogRecord_t));
            
            uint32_t currentSector = logAddress / 4096;
            uint32_t previousSector;
            
            if (hoursUptime == 1) {
                previousSector = 0; 
            } else {
                uint32_t prevAddress = FLASH_ADDR_LOG_BASE + ((hoursUptime - 2) * sizeof(LogRecord_t));
                previousSector = prevAddress / 4096;
            }

            // Sector Management: If the log rolls over into a new 4KB sector, erase it before writing
            if ((currentSector > previousSector) || (hoursUptime == 1)) 
            { 
                uint32_t sectorBaseAddress = FLASH_ADDR_LOG_BASE + (currentSector * 4096);
                Flash_EraseSector(sectorBaseAddress); 
            }
            
            // Write the struct via pointer casting directly to hardware
            Flash_WriteData(logAddress, (uint8_t*)&rec, sizeof(LogRecord_t));
            
            powerDownSpi(); 
            
            Display_print0(dispHandle, 0, 0, "");
            Display_print0(dispHandle, 0, 0, "    [ --- Memory Saved Internal & External --- ]     ");
        } 
        else 
        {
            Display_print0(dispHandle, 0, 0, "");
            Display_print0(dispHandle, 0, 0, "      [ --- Memory Saved to Internal Only --- ]      ");
        }
        
        Display_print0(dispHandle, 0, 0, "=====================================================");
        
        // Dynamically update the BLE Advertisement payload so clients get real-time strength data without pairing
        int strWhole = (int)compressiveStrength;
        int strFrac  = (int)((compressiveStrength - strWhole) * 10000); 
        if (strFrac < 0) strFrac = -strFrac;
        if (strWhole < 0) strWhole = 0; 
        
        advertData[7]  = '0' + (strWhole / 1000) % 10;
        advertData[8]  = '0' + (strWhole / 100) % 10;
        advertData[9]  = '0' + (strWhole / 10) % 10;
        advertData[10] = '0' + (strWhole % 10);
        
        advertData[12] = '0' + (strFrac / 1000) % 10;
        advertData[13] = '0' + (strFrac / 100) % 10;
        advertData[14] = '0' + (strFrac / 10) % 10;
        advertData[15] = '0' + (strFrac % 10);
        
        // Push payload changes into the active GAP role stack
        if (gapProfileState != GAPROLE_CONNECTED)
        {
            if (isBLEAdvertising) 
            {
                // Must toggle advertising state off and on for the new data pointer to take effect
                uint8_t advertEnable = FALSE;
                GAPRole_SetParameter(GAPROLE_ADVERT_ENABLED, sizeof(uint8_t), &advertEnable); 
                GAPRole_SetParameter(GAPROLE_ADVERT_DATA, sizeof(advertData), advertData);
                
                advertEnable = TRUE;
                GAPRole_SetParameter(GAPROLE_ADVERT_ENABLED, sizeof(uint8_t), &advertEnable);
            } 
            else 
            {
                GAPRole_SetParameter(GAPROLE_ADVERT_DATA, sizeof(advertData), advertData);
            }
        }

        // Reset the accumulators for the next hour
        tempAccumulator = 0.0f;
        sampleCount = 0;

        osal_snv_write(SNV_ID_SAMPLE_COUNT, sizeof(uint8_t), &sampleCount);
        osal_snv_write(SNV_ID_TEMP_ACCUM, sizeof(float), &tempAccumulator);
    }
}

// Routes RTOS clock ticks to the main thread via flags
static void SimpleBLEPeripheral_clockHandler(UArg arg)
{
    events |= arg;
    Semaphore_post(sem);
}

// Safely creates standard application messages and drops them in the queue
static void SimpleBLEPeripheral_enqueueMsg(uint8_t event, uint8_t state)
{
    sbpEvt_t *pMsg;
    
    if ((pMsg = ICall_malloc(sizeof(sbpEvt_t))))
    {
        pMsg->hdr.event = event;
        pMsg->hdr.state = state;
        Util_enqueueMsg(appMsgQueue, sem, (uint8*)pMsg);
    }
}
