/******************************************************************************

 @file  simple_peripheral.c

 @brief This file contains the Simple BLE Peripheral sample application for use
        with the CC2650 Bluetooth Low Energy Protocol Stack.
 *****************************************************************************/

/*********************************************************************
 * INCLUDES
 */
#include <string.h>
#include <stdbool.h>

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
#endif //FEATURE_OAD || IMAGE_INVALIDATE

#include "peripheral.h"
#include "gapbondmgr.h"
#include "gap.h"

// --- RESTORED INCLUDE TO FIX COMPILER ERRORS ---
#include "osal_snv.h" 
#include "icall_apimsg.h"
#include "util.h"

#ifdef USE_RCOSC
#include "rcosc_calibration.h"
#endif //USE_RCOSC

#include "board_key.h"
#include "board.h"
#include "simple_peripheral.h"

#include <driverlib/sys_ctrl.h>

#if defined( USE_FPGA ) || defined( DEBUG_SW_TRACE )
#include <driverlib/ioc.h>
#endif // USE_FPGA | DEBUG_SW_TRACE

/*********************************************************************
 * CONSTANTS
 */

#define DEFAULT_ADVERTISING_INTERVAL          800
#define DEFAULT_DISCOVERABLE_MODE             GAP_ADTYPE_FLAGS_GENERAL

#ifndef FEATURE_OAD
#define DEFAULT_DESIRED_MIN_CONN_INTERVAL     80
#define DEFAULT_DESIRED_MAX_CONN_INTERVAL     800
#else //!FEATURE_OAD
#define DEFAULT_DESIRED_MIN_CONN_INTERVAL     8
#define DEFAULT_DESIRED_MAX_CONN_INTERVAL     8
#endif // FEATURE_OAD

#define DEFAULT_DESIRED_SLAVE_LATENCY         0
#define DEFAULT_DESIRED_CONN_TIMEOUT          1000
#define DEFAULT_ENABLE_UPDATE_REQUEST         GAPROLE_LINK_PARAM_UPDATE_INITIATE_BOTH_PARAMS
#define DEFAULT_CONN_PAUSE_PERIPHERAL         6

// --- FAST TESTING TIMING ---
// 10000ms (10 seconds) for 6 readings per minute
#define SBP_PERIODIC_EVT_PERIOD               10000 

#ifdef FEATURE_OAD
#define OAD_PACKET_SIZE                       ((OAD_BLOCK_SIZE) + 2)
#endif // FEATURE_OAD

#define SBP_TASK_PRIORITY                     1

#ifndef SBP_TASK_STACK_SIZE
#define SBP_TASK_STACK_SIZE                   644
#endif

// --- EVENT FLAGS ---
#define SBP_STATE_CHANGE_EVT                  0x0001
#define SBP_CHAR_CHANGE_EVT                   0x0002
#define SBP_PERIODIC_EVT                      0x0004
#define SBP_CONN_EVT_END_EVT                  0x0008
#define SBP_BTN_EVT                           0x0010 // NEW EVENT FOR BUTTON 2 DUMP

/*********************************************************************
 * TYPEDEFS
 */
typedef struct
{
  appEvtHdr_t hdr; // event header.
} sbpEvt_t;

// --- EXTERNAL MEMORY STRUCTURES ---
#define FLASH_MAGIC_WORD 0xAABBCCDD
#define FLASH_ADDR_PRIMARY 0x000000 // Sector 0
#define FLASH_ADDR_BACKUP  0x001000 // Sector 1
#define FLASH_ADDR_LOG_BASE 0x002000 // Sector 2+

typedef struct {
    uint32_t magic;
    uint32_t hoursUptime;
    float cumulativeMaturity;
} StateData_t;

typedef struct {
    uint32_t minute;
    float avgTemp;
    float newMaturitySlice;
    float cumulativeMaturity;
} LogRecord_t;

/*********************************************************************
 * GLOBAL VARIABLES
 */
Display_Handle dispHandle = NULL;
static I2C_Handle i2c;

// --- MATURITY TRACKING VARIABLES ---
#define DATUM_TEMPERATURE -10.0f
static float tempAccumulator = 0.0f;
static uint8_t sampleCount = 0;
static uint32_t hoursUptime = 0; // Represents minutes in this fast-test version
static float cumulativeMaturity = 0.0f;

// --- SPI FLASH VARIABLES ---
static SPI_Handle spiHandle;
static SPI_Params spiParams;
static PIN_Handle flashCsPinHandle;
static PIN_State  flashCsPinState;

static PIN_Config flashCsPinTable[] = {
    Board_SPI_FLASH_CS | PIN_GPIO_OUTPUT_EN | PIN_GPIO_HIGH | PIN_PUSHPULL | PIN_DRVSTR_MIN,
    PIN_TERMINATE
};

// --- BUTTON 2 VARIABLES ---
static PIN_Handle btnPinHandle;
static PIN_State  btnPinState;

static PIN_Config btnPinTable[] = {
    Board_BTN2 | PIN_INPUT_EN | PIN_PULLUP | PIN_IRQ_NEGEDGE,
    PIN_TERMINATE
};

/*********************************************************************
 * LOCAL VARIABLES
 */
static ICall_EntityID selfEntity;
static ICall_Semaphore sem;

static Clock_Struct periodicClock;
static bool isBLEAdvertising = true;

static Queue_Struct appMsg;
static Queue_Handle appMsgQueue;

#if defined(FEATURE_OAD)
static Queue_Struct oadQ;
static Queue_Handle hOadQ;
#endif //FEATURE_OAD

static uint16_t events;
Task_Struct sbpTask;
Char sbpTaskStack[SBP_TASK_STACK_SIZE];

static uint8_t scanRspData[] =
{
  0x0F,
  GAP_ADTYPE_LOCAL_NAME_COMPLETE,
  'M','a','t','u','r','i','t','y',' ','I','n','d','e','x'
};

static uint8_t advertData[] =
{
  0x02,
  GAP_ADTYPE_FLAGS,
  GAP_ADTYPE_FLAGS_GENERAL | GAP_ADTYPE_FLAGS_BREDR_NOT_SUPPORTED,
  
  0x0C,
  GAP_ADTYPE_MANUFACTURER_SPECIFIC,
  0x0D, 0x00, 
  '0','0','0','0','.','0','0','0','0' 
};

static uint8_t attDeviceName[GAP_DEVICE_NAME_LEN] = "Maturity Index";
static gattMsgEvent_t *pAttRsp = NULL;
static uint8_t rspTxRetry = 0;

/*********************************************************************
 * LOCAL FUNCTIONS
 */
static void SimpleBLEPeripheral_init( void );
static void SimpleBLEPeripheral_taskFxn(UArg a0, UArg a1);
static uint8_t SimpleBLEPeripheral_processStackMsg(ICall_Hdr *pMsg);
static uint8_t SimpleBLEPeripheral_processGATTMsg(gattMsgEvent_t *pMsg);
static void SimpleBLEPeripheral_processAppMsg(sbpEvt_t *pMsg);
static void SimpleBLEPeripheral_processStateChangeEvt(gaprole_States_t newState);
static void SimpleBLEPeripheral_processCharValueChangeEvt(uint8_t paramID);
static void SimpleBLEPeripheral_performPeriodicTask(void);
static void SimpleBLEPeripheral_clockHandler(UArg arg);
static void SimpleBLEPeripheral_sendAttRsp(void);
static void SimpleBLEPeripheral_freeAttRsp(uint8_t status);
static void SimpleBLEPeripheral_stateChangeCB(gaprole_States_t newState);

// New Helper Functions
static void btnCallbackFxn(PIN_Handle handle, PIN_Id pinId);
static void initExtFlash(void);
static void Flash_WaitReady(void);
static void Flash_WriteEnable(void);
static void Flash_EraseSector(uint32_t addr);
static void Flash_WriteData(uint32_t addr, uint8_t *data, uint16_t len);
static void Flash_ReadData(uint32_t addr, uint8_t *data, uint16_t len);

#ifndef FEATURE_OAD_ONCHIP
static void SimpleBLEPeripheral_charValueChangeCB(uint8_t paramID);
#endif //!FEATURE_OAD_ONCHIP

static void SimpleBLEPeripheral_enqueueMsg(uint8_t event, uint8_t state);

#ifdef FEATURE_OAD
void SimpleBLEPeripheral_processOadWriteCB(uint8_t event, uint16_t connHandle, uint8_t *pData);
#endif //FEATURE_OAD

extern void AssertHandler(uint8 assertCause, uint8 assertSubcause);

/*********************************************************************
 * PROFILE CALLBACKS
 */
static gapRolesCBs_t SimpleBLEPeripheral_gapRoleCBs = { SimpleBLEPeripheral_stateChangeCB };
static gapBondCBs_t simpleBLEPeripheral_BondMgrCBs = { NULL, NULL };

#ifndef FEATURE_OAD_ONCHIP
static simpleProfileCBs_t SimpleBLEPeripheral_simpleProfileCBs = { SimpleBLEPeripheral_charValueChangeCB };
#endif //!FEATURE_OAD_ONCHIP

#ifdef FEATURE_OAD
static oadTargetCBs_t simpleBLEPeripheral_oadCBs = { SimpleBLEPeripheral_processOadWriteCB };
#endif //FEATURE_OAD

/*********************************************************************
 * PUBLIC FUNCTIONS
 */
void SimpleBLEPeripheral_createTask(void)
{
  Task_Params taskParams;
  Task_Params_init(&taskParams);
  taskParams.stack = sbpTaskStack;
  taskParams.stackSize = SBP_TASK_STACK_SIZE;
  taskParams.priority = SBP_TASK_PRIORITY;
  Task_construct(&sbpTask, SimpleBLEPeripheral_taskFxn, &taskParams, NULL);
}

// --- BUTTON INTERRUPT HANDLER ---
static void btnCallbackFxn(PIN_Handle handle, PIN_Id pinId) {
    if (pinId == Board_BTN2) {
        events |= SBP_BTN_EVT;
        Semaphore_post(sem);
    }
}

// --- SPI FLASH DRIVER FUNCTIONS ---
static void initExtFlash(void) {
    flashCsPinHandle = PIN_open(&flashCsPinState, flashCsPinTable);
    SPI_Params_init(&spiParams);
    spiParams.bitRate     = 2000000;      // 2 MHz
    spiParams.frameFormat = SPI_POL0_PHA0; 
    spiParams.mode        = SPI_MASTER;
    spiHandle = SPI_open(Board_SPI0, &spiParams);
}

static void Flash_WaitReady(void) {
    uint8_t tx[2] = {0x05, 0x00}; // Read Status Register 1
    uint8_t rx[2] = {0, 0};
    SPI_Transaction t = { .count = 2, .txBuf = tx, .rxBuf = rx };
    do {
        PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 0);
        SPI_transfer(spiHandle, &t);
        PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 1);
    } while(rx[1] & 0x01); // Wait while BUSY bit is 1
}

static void Flash_WriteEnable(void) {
    uint8_t tx[1] = {0x06}; // Write Enable Command
    SPI_Transaction t = { .count = 1, .txBuf = tx, .rxBuf = NULL };
    PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 0);
    SPI_transfer(spiHandle, &t);
    PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 1);
}

static void Flash_EraseSector(uint32_t addr) {
    Flash_WriteEnable();
    uint8_t tx[4] = {0x20, (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF};
    SPI_Transaction t = { .count = 4, .txBuf = tx, .rxBuf = NULL };
    PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 0);
    SPI_transfer(spiHandle, &t);
    PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 1);
    Flash_WaitReady();
}

static void Flash_WriteData(uint32_t addr, uint8_t *data, uint16_t len) {
    Flash_WriteEnable();
    uint8_t tx[4] = {0x02, (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF};
    SPI_Transaction t1 = { .count = 4, .txBuf = tx, .rxBuf = NULL };
    SPI_Transaction t2 = { .count = len, .txBuf = data, .rxBuf = NULL };

    PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 0);
    SPI_transfer(spiHandle, &t1);
    SPI_transfer(spiHandle, &t2);
    PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 1);
    Flash_WaitReady();
}

static void Flash_ReadData(uint32_t addr, uint8_t *data, uint16_t len) {
    uint8_t tx[4] = {0x03, (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF};
    SPI_Transaction t1 = { .count = 4, .txBuf = tx, .rxBuf = NULL };
    SPI_Transaction t2 = { .count = len, .txBuf = NULL, .rxBuf = data };

    PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 0);
    SPI_transfer(spiHandle, &t1);
    SPI_transfer(spiHandle, &t2);
    PIN_setOutputValue(flashCsPinHandle, Board_SPI_FLASH_CS, 1);
}


static void SimpleBLEPeripheral_init(void)
{
  ICall_registerApp(&selfEntity, &sem);

#ifdef USE_RCOSC
  RCOSC_enableCalibration();
#endif // USE_RCOSC

  appMsgQueue = Util_constructQueue(&appMsg);

  Util_constructClock(&periodicClock, SimpleBLEPeripheral_clockHandler,
                      SBP_PERIODIC_EVT_PERIOD, SBP_PERIODIC_EVT_PERIOD, true, SBP_PERIODIC_EVT);

  dispHandle = Display_open(Display_Type_UART, NULL);
  
  // Initialize External SPI Flash
  initExtFlash();

  // Initialize Button 2 with Interrupt
  btnPinHandle = PIN_open(&btnPinState, btnPinTable);
  PIN_registerIntCb(btnPinHandle, btnCallbackFxn);

  GAP_SetParamValue(TGAP_CONN_PAUSE_PERIPHERAL, DEFAULT_CONN_PAUSE_PERIPHERAL);

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
  {
    uint16_t advInt = DEFAULT_ADVERTISING_INTERVAL;
    GAP_SetParamValue(TGAP_LIM_DISC_ADV_INT_MIN, advInt);
    GAP_SetParamValue(TGAP_LIM_DISC_ADV_INT_MAX, advInt);
    GAP_SetParamValue(TGAP_GEN_DISC_ADV_INT_MIN, advInt);
    GAP_SetParamValue(TGAP_GEN_DISC_ADV_INT_MAX, advInt);
  }

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

  GGS_AddService(GATT_ALL_SERVICES);
  GATTServApp_AddService(GATT_ALL_SERVICES);
  DevInfo_AddService();

#ifndef FEATURE_OAD_ONCHIP
  SimpleProfile_AddService(GATT_ALL_SERVICES);
  
  // FIX: Registered the App Callbacks so your app can receive BLE commands!
  SimpleProfile_RegisterAppCBs(&SimpleBLEPeripheral_simpleProfileCBs);
#endif //!FEATURE_OAD_ONCHIP

  /* --------- SENSOR INIT --------- */
  I2C_init();

  // --- EXTERNAL FLASH MEMORY RESTORE, BACKUP, OR RESET LOGIC ---
  uint32_t resetSource = SysCtrlResetSourceGet();
  StateData_t sd;

  if (resetSource == RSTSRC_PIN_RESET) 
  {
      hoursUptime = 0;
      cumulativeMaturity = 0.0f;
      sd.magic = FLASH_MAGIC_WORD;
      sd.hoursUptime = hoursUptime;
      sd.cumulativeMaturity = cumulativeMaturity;

      Flash_EraseSector(FLASH_ADDR_PRIMARY);
      Flash_WriteData(FLASH_ADDR_PRIMARY, (uint8_t*)&sd, sizeof(StateData_t));
      Flash_EraseSector(FLASH_ADDR_BACKUP);
      Flash_WriteData(FLASH_ADDR_BACKUP, (uint8_t*)&sd, sizeof(StateData_t));
      Flash_EraseSector(FLASH_ADDR_LOG_BASE); // Clear first log sector
      
      Display_print0(dispHandle, 0, 0, "EXT MEMORY: RESET Button Pressed. Wiped to 0.");
  } 
  else 
  {
      // 2. Read Primary Memory from External Flash
      Flash_ReadData(FLASH_ADDR_PRIMARY, (uint8_t*)&sd, sizeof(StateData_t));

      if (sd.magic == FLASH_MAGIC_WORD && sd.cumulativeMaturity >= 0.0f && sd.cumulativeMaturity <= 100000.0f) 
      {
          hoursUptime = sd.hoursUptime;
          cumulativeMaturity = sd.cumulativeMaturity;
      } 
      else 
      {
          // Primary Memory corrupted. Try BACKUP.
          Flash_ReadData(FLASH_ADDR_BACKUP, (uint8_t*)&sd, sizeof(StateData_t));

          if (sd.magic == FLASH_MAGIC_WORD && sd.cumulativeMaturity >= 0.0f && sd.cumulativeMaturity <= 100000.0f) 
          {
              hoursUptime = sd.hoursUptime;
              cumulativeMaturity = sd.cumulativeMaturity;

              int mWhole = (int)cumulativeMaturity;
              int mFrac = (int)((cumulativeMaturity - mWhole) * 10000); if (mFrac < 0) mFrac = -mFrac;

              Display_print0(dispHandle, 0, 0, "!! WARNING: EXT PRIMARY MEMORY CORRUPTED !!");
              Display_print2(dispHandle, 0, 0, "Restored previous correct value: %d.%04d", mWhole, mFrac);

              // Restore Primary
              Flash_EraseSector(FLASH_ADDR_PRIMARY);
              Flash_WriteData(FLASH_ADDR_PRIMARY, (uint8_t*)&sd, sizeof(StateData_t));
          }
          else
          {
              hoursUptime = 0;
              cumulativeMaturity = 0.0f;
              sd.magic = FLASH_MAGIC_WORD;
              sd.hoursUptime = hoursUptime;
              sd.cumulativeMaturity = cumulativeMaturity;

              Flash_EraseSector(FLASH_ADDR_PRIMARY);
              Flash_WriteData(FLASH_ADDR_PRIMARY, (uint8_t*)&sd, sizeof(StateData_t));
              Flash_EraseSector(FLASH_ADDR_BACKUP);
              Flash_WriteData(FLASH_ADDR_BACKUP, (uint8_t*)&sd, sizeof(StateData_t));
              Flash_EraseSector(FLASH_ADDR_LOG_BASE);
              
              Display_print0(dispHandle, 0, 0, "!! CRITICAL: ALL EXT MEMORY CORRUPTED !!");
              Display_print0(dispHandle, 0, 0, "Cannot recover. Starting fresh at 0.0000");
          }
      }
  }
  
  int matWhole = (int)cumulativeMaturity;
  int matFrac = (int)((cumulativeMaturity - matWhole) * 10000); 
  if (matFrac < 0) matFrac = -matFrac;
  advertData[7]  = '0' + (matWhole / 1000) % 10;
  advertData[8]  = '0' + (matWhole / 100) % 10;
  advertData[9]  = '0' + (matWhole / 10) % 10;
  advertData[10] = '0' + (matWhole % 10);
  advertData[12] = '0' + (matFrac / 1000) % 10;
  advertData[13] = '0' + (matFrac / 100) % 10;
  advertData[14] = '0' + (matFrac / 10) % 10;
  advertData[15] = '0' + (matFrac % 10);

  GAPRole_SetParameter(GAPROLE_ADVERT_DATA, sizeof(advertData), advertData);
  VOID GAPRole_StartDevice(&SimpleBLEPeripheral_gapRoleCBs);
  VOID GAPBondMgr_Register(&simpleBLEPeripheral_BondMgrCBs);
  GAP_RegisterForMsgs(selfEntity);
  GATT_RegisterForMsgs(selfEntity);
  HCI_LE_ReadMaxDataLenCmd();
}

static void SimpleBLEPeripheral_taskFxn(UArg a0, UArg a1)
{
  SimpleBLEPeripheral_init();
  for (;;)
  {
    ICall_Errno errno = ICall_wait(ICALL_TIMEOUT_FOREVER);
    if (errno == ICALL_ERRNO_SUCCESS)
    {
      ICall_EntityID dest;
      ICall_ServiceEnum src;
      ICall_HciExtEvt *pMsg = NULL;

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

    // --- BUTTON 2 EVENT: DUMP FLASH DATA TO SERIAL CONSOLE ---
    if (events & SBP_BTN_EVT)
    {
        events &= ~SBP_BTN_EVT;
        
        Display_print0(dispHandle, 0, 0, "\n\r===========================================");
        Display_print0(dispHandle, 0, 0, "     --- EXTERNAL FLASH LOG DUMP ---       ");
        Display_print0(dispHandle, 0, 0, "===========================================");
        
        if (hoursUptime == 0) {
            Display_print0(dispHandle, 0, 0, "No data recorded yet.");
        } else {
            for (uint32_t i = 1; i <= hoursUptime; i++) {
                LogRecord_t rec;
                // Calculate memory address for this specific minute's record
                uint32_t recAddress = FLASH_ADDR_LOG_BASE + ((i - 1) * sizeof(LogRecord_t));
                Flash_ReadData(recAddress, (uint8_t*)&rec, sizeof(LogRecord_t));

                int cWhole = (int)rec.avgTemp;
                int cFrac = (int)((rec.avgTemp - cWhole) * 100); if (cFrac < 0) cFrac = -cFrac;
                
                int mWhole = (int)rec.cumulativeMaturity;
                int mFrac = (int)((rec.cumulativeMaturity - mWhole) * 10000); if (mFrac < 0) mFrac = -mFrac;

                // FIX: Display_print5 for 5 parameters
                Display_print5(dispHandle, 0, 0, "Min %d | AvgTemp: %d.%02d C | Maturity: %d.%04d", 
                               rec.minute, cWhole, cFrac, mWhole, mFrac);
            }
        }
        Display_print0(dispHandle, 0, 0, "===========================================\n\r");
    }

    // --- SENSOR PERIODIC TASK ---
    if (events & SBP_PERIODIC_EVT)
    {
      events &= ~SBP_PERIODIC_EVT;
      Util_startClock(&periodicClock);
      SimpleBLEPeripheral_performPeriodicTask();
    }
  }
}

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

static void SimpleBLEPeripheral_stateChangeCB(gaprole_States_t newState)
{
  SimpleBLEPeripheral_enqueueMsg(SBP_STATE_CHANGE_EVT, newState);
}

static void SimpleBLEPeripheral_processStateChangeEvt(gaprole_States_t newState)
{
  switch ( newState )
  {
    case GAPROLE_STARTED:
      {
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
      Display_print0(dispHandle, 0, 0, ">> BLE is Advertising");
      break;
    case GAPROLE_CONNECTED:
      {
        linkDBInfo_t linkInfo;
        uint8_t numActive = 0;
        numActive = linkDB_NumActive();

        if ( linkDB_GetInfo( numActive - 1, &linkInfo ) == SUCCESS )
        {
          // Empty
        }
      }
      break;
    case GAPROLE_CONNECTED_ADV:
      break;

    case GAPROLE_WAITING:
      {
        uint8_t advertReEnable = TRUE;
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
#endif //!FEATURE_OAD_ONCHIP

static void SimpleBLEPeripheral_processCharValueChangeEvt(uint8_t paramID)
{
#ifndef FEATURE_OAD_ONCHIP
  uint8_t newValue;
  switch(paramID)
  {
    case SIMPLEPROFILE_CHAR1:
      SimpleProfile_GetParameter(SIMPLEPROFILE_CHAR1, &newValue);
      if (newValue == 0) 
      {
          hoursUptime = 0;
          cumulativeMaturity = 0.0f;
          
          StateData_t sd;
          sd.magic = FLASH_MAGIC_WORD;
          sd.hoursUptime = hoursUptime;
          sd.cumulativeMaturity = cumulativeMaturity;

          Flash_EraseSector(FLASH_ADDR_PRIMARY);
          Flash_WriteData(FLASH_ADDR_PRIMARY, (uint8_t*)&sd, sizeof(StateData_t));
          Flash_EraseSector(FLASH_ADDR_BACKUP);
          Flash_WriteData(FLASH_ADDR_BACKUP, (uint8_t*)&sd, sizeof(StateData_t));
          Flash_EraseSector(FLASH_ADDR_LOG_BASE);
          
          Display_print0(dispHandle, 0, 0, "=================================");
          Display_print0(dispHandle, 0, 0, "BLE COMMAND: EXT MEMORY WIPED!!!");
          Display_print0(dispHandle, 0, 0, "=================================");
          advertData[7]  = '0';
          advertData[8]  = '0'; advertData[9]  = '0'; advertData[10] = '0';
          advertData[12] = '0'; advertData[13] = '0'; advertData[14] = '0';
          advertData[15] = '0';
          
          if (isBLEAdvertising) {
              uint8_t advertEnable = FALSE;
              GAPRole_SetParameter(GAPROLE_ADVERT_ENABLED, sizeof(uint8_t), &advertEnable); 
              GAPRole_SetParameter(GAPROLE_ADVERT_DATA, sizeof(advertData), advertData);
              advertEnable = TRUE;
              GAPRole_SetParameter(GAPROLE_ADVERT_ENABLED, sizeof(uint8_t), &advertEnable);
          } else {
              GAPRole_SetParameter(GAPROLE_ADVERT_DATA, sizeof(advertData), advertData);
          }
      }
      break;
    case SIMPLEPROFILE_CHAR3:
      SimpleProfile_GetParameter(SIMPLEPROFILE_CHAR3, &newValue);
      break;
  }
#endif //!FEATURE_OAD_ONCHIP
}

static void SimpleBLEPeripheral_performPeriodicTask(void)
{
    I2C_Params i2cParams;
    I2C_Params_init(&i2cParams);
    i2cParams.bitRate = I2C_400kHz;
    i2c = I2C_open(Board_I2C, &i2cParams);

    if(i2c == NULL) {
        Display_print0(dispHandle, 0, 0, "I2C ERROR - DRIVER FAILED TO OPEN");
        return; 
    }

    uint8_t txBuf[1] = {0x00};
    uint8_t rxBuf[2] = {0, 0}; 
    I2C_Transaction i2cTransaction;

    memset(&i2cTransaction, 0, sizeof(I2C_Transaction));

    i2cTransaction.slaveAddress = 0x48;
    i2cTransaction.writeBuf   = txBuf;
    i2cTransaction.writeCount = 1;
    i2cTransaction.readBuf    = rxBuf;
    i2cTransaction.readCount  = 2;
    if (I2C_transfer(i2c, &i2cTransaction))
    {
        I2C_close(i2c);
        int16_t rawTemp = (rxBuf[0] << 4) | (rxBuf[1] >> 4);
        if (rawTemp & 0x0800) rawTemp |= 0xF000;
        float currentTemp = rawTemp * 0.0625f;
        tempAccumulator += currentTemp;
        sampleCount++;
        
        int cWhole = (int)currentTemp;
        int cFrac = (int)((currentTemp - cWhole) * 100);
        if (cFrac < 0) cFrac = -cFrac;
        Display_print3(dispHandle, 0, 0, "  [Sample %d/6] Current Sample Temp      : %d.%02d C", sampleCount, cWhole, cFrac);
        
        if (sampleCount >= 6) 
        {
            hoursUptime++;
            float averageTemp = tempAccumulator / 6.0f;
            float previousMaturity = cumulativeMaturity;
            float newMaturitySlice = 0.0f;

            if (averageTemp > DATUM_TEMPERATURE) {
                float timeStepHours = 1.0f / 60.0f;
                newMaturitySlice = (averageTemp - DATUM_TEMPERATURE) * timeStepHours;
                cumulativeMaturity = previousMaturity + newMaturitySlice;
            }

            int avgWhole = (int)averageTemp;
            int avgFrac = (int)((averageTemp - avgWhole) * 100);
            if (avgFrac < 0) avgFrac = -avgFrac;

            int prevWhole = (int)previousMaturity;
            int prevFrac = (int)((previousMaturity - prevWhole) * 10000); 
            if (prevFrac < 0) prevFrac = -prevFrac;

            int sliceWhole = (int)newMaturitySlice;
            int sliceFrac = (int)((newMaturitySlice - sliceWhole) * 10000); 
            if (sliceFrac < 0) sliceFrac = -sliceFrac;

            int matWhole = (int)cumulativeMaturity;
            int matFrac = (int)((cumulativeMaturity - matWhole) * 10000); 
            if (matFrac < 0) matFrac = -matFrac;
            
            Display_print0(dispHandle, 0, 0, "=====================================================");
            Display_print1(dispHandle, 0, 0, " TIME                         : %d Minute(s) Elapsed", hoursUptime);
            Display_print2(dispHandle, 0, 0, " 1-MIN AVG TEMP               : %d.%02d C", avgWhole, avgFrac);
            if (hoursUptime == 1) {
                Display_print0(dispHandle, 0, 0, " Previous Maturity Index      : 0.0000 Deg-Hr");
            } else {
                Display_print2(dispHandle, 0, 0, " Previous Maturity Index      : %d.%04d Deg-Hr", prevWhole, prevFrac);
            }
            Display_print2(dispHandle, 0, 0, " Current 1-MIN Maturity Slice : %d.%04d Deg-Hr", sliceWhole, sliceFrac);
            Display_print2(dispHandle, 0, 0, " Final Maturity Index         : %d.%04d Deg-Hr", matWhole, matFrac);

            // --- SAVE TO EXTERNAL FLASH MEMORY ---
            // 1. Update State (Primary and Backup)
            StateData_t sd;
            sd.magic = FLASH_MAGIC_WORD;
            sd.hoursUptime = hoursUptime;
            sd.cumulativeMaturity = cumulativeMaturity;
            
            Flash_EraseSector(FLASH_ADDR_PRIMARY);
            Flash_WriteData(FLASH_ADDR_PRIMARY, (uint8_t*)&sd, sizeof(StateData_t));
            
            Flash_EraseSector(FLASH_ADDR_BACKUP);
            Flash_WriteData(FLASH_ADDR_BACKUP, (uint8_t*)&sd, sizeof(StateData_t));

            // 2. Append Historical Log Record
            LogRecord_t rec;
            rec.minute = hoursUptime;
            rec.avgTemp = averageTemp;
            rec.newMaturitySlice = newMaturitySlice;
            rec.cumulativeMaturity = cumulativeMaturity;

            // Calculate address. If crossing a 4KB boundary (every 256 logs), erase new sector.
            uint32_t logAddress = FLASH_ADDR_LOG_BASE + ((hoursUptime - 1) * sizeof(LogRecord_t));
            if ((logAddress % 4096) == 0) {
                Flash_EraseSector(logAddress);
            }
            Flash_WriteData(logAddress, (uint8_t*)&rec, sizeof(LogRecord_t));

            Display_print0(dispHandle, 0, 0, " [Saved to External Flash Memory]");
            Display_print0(dispHandle, 0, 0, "=====================================================");
            
            advertData[7]  = '0' + (matWhole / 1000) % 10;
            advertData[8]  = '0' + (matWhole / 100) % 10;
            advertData[9]  = '0' + (matWhole / 10) % 10;
            advertData[10] = '0' + (matWhole % 10);
            
            advertData[12] = '0' + (matFrac / 1000) % 10;
            advertData[13] = '0' + (matFrac / 100) % 10;
            advertData[14] = '0' + (matFrac / 10) % 10;
            advertData[15] = '0' + (matFrac % 10);
            
            if (isBLEAdvertising) {
                uint8_t advertEnable = FALSE;
                GAPRole_SetParameter(GAPROLE_ADVERT_ENABLED, sizeof(uint8_t), &advertEnable); 
                GAPRole_SetParameter(GAPROLE_ADVERT_DATA, sizeof(advertData), advertData);
                
                advertEnable = TRUE;
                GAPRole_SetParameter(GAPROLE_ADVERT_ENABLED, sizeof(uint8_t), &advertEnable);
            } else {
                GAPRole_SetParameter(GAPROLE_ADVERT_DATA, sizeof(advertData), advertData);
            }

            tempAccumulator = 0.0f;
            sampleCount = 0;
        }
    }
    else
    {
        I2C_close(i2c);
        Display_print0(dispHandle, 0, 0, "!! SENSOR READ FAILED !!");
    }
}

static void SimpleBLEPeripheral_clockHandler(UArg arg)
{
  events |= arg;
  Semaphore_post(sem);
}

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