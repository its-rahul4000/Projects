# ***Source Code Guidelines and Explanations***

# ***1. Code Directory Structure***

```
C:\ti\simplelink\ble_sdk_2_02_05_02\examples\cc2650lp\simple_peripheral\
│
├── ccs
│   ├── App
│   │   ├── Application
│   │   │   ├── Final_Deployment.c     # Main application
│   │   │   ├── CC2650_LaunchXL.c       # Peripheral driver configurations
│   │   │   ├── CC2650_LaunchXL.h       # Custom pin mapping & board definitions
│   │   |
│   |── Stack                       # BLE Stack/Protocol source files
```

---
# ***2. Hardware Pin Configuration***

The system uses custom pin mapping for I²C sensor and external SPI flash.

### TMP1075 (I²C Sensor)

- (0)SDA → DIO_0  
- (1)SCL → DIO_1  

### External SPI Flash (SPI)

- (6)CLK  → DIO_8  
- (5)MOSI/DI → DIO_9  
- (2)MISO/DO → DIO_10  
- (1)CS   → DIO_11  

### UART (Optional Debug)

- RX → IOID_6  
- TX ← IOID_5  

### LaunchPad  →  CC2650 MODA(JTAG Configuration)
- RST        →  RESET_N
- TCK        →  JTAG_TCK
- TMS        →  JTAG_TMS
- GND        ↔  GND
- 3V3        →  VDD

---

# ***3. Installation & Setup (CC2650 LaunchXL)***

Follow these steps to set up the development environment correctly.

---

## ***📥 Required Downloads***

### 1. IDE- Code Composer Studio (CCS)
Version: 20.4.1  
https://www.ti.com/tool/download/CCSTUDIO/20.4.1  

---

### 2. BLE Stack SDK  
Package: BLE-STACK-2-X  
Version: 2.02.05.02  
https://www.ti.com/tool/download/BLE-STACK-2-X/2.02.05.02  

---

### 3. TI-RTOS SDK  
Version: 2.21.01.08  
https://downloads.ti.com/dsps/dsps_public_sw/sdo_sb/targetcontent/tirtos/index.html  

---

### 4. ARM Compiler (Required for CC2650)
Version: 16.9.4.LTS  
https://www.ti.com/tool/download/ARM-CGT/16.9.4.LTS  

---

## ***⚠️ Important Compiler Setup***

Install the ARM compiler **exactly at this path**:

```
C:\ti\ccs2041\ccs\tools\compiler\ti-cgt-arm_16.9.4.LTS
```

---

## ***⚙️ CCS Configuration Steps***

### Add Compiler
- Open CCS
- Go to:  
  `Settings → Code Composer Studio Settings → Compiler`
- Click ➕ (Add)
- Select:

```
C:\ti\ccs2041\ccs\tools\compiler\ti-cgt-arm_16.9.4.LTS
```

---

### Add TI-RTOS Product

- Again go to:  
  `Settings → Code Composer Studio Settings → Products`
- Click ➕ (Add)
- Select:

```
C:\ti\tirtos_cc13xx_cc26xx_2_21_01_08
```

---


# ***4. How to Import, Build & Run the Project (in CCS)***


## ***📥 Step 1: Open Code Composer Studio (CCS)***

- Launch **Code Composer Studio (CCS)**
- Wait for the workspace to load

---

## ***📂 Step 2: Import the Project***

1. Go to menu:
   ```
   File → Import Projects...
   ```

2. In the "Import Projects" window:
   - Click **Browse**
   - Navigate to:

   ```
   C:\ti\simplelink\ble_sdk_2_02_05_02\examples\cc2650lp\simple_peripheral
   ```

3. CCS will automatically detect two projects:

   - `simple_peripheral_cc2650lp_app`
   - `simple_peripheral_cc2650lp_stack`

4. Select **both projects**

5. Click **Finish**

---
## ***📂 Step 4: Copy and Paste only these codes file only***

   - `simple_peripheral.c`

   - ` CC2650_LAUNCHXL.c `
   - ` CC2650_LAUNCHXL.h `


---

## ***🧹 Step 4: Clean the Project***

- Right-click on both app and stack folder (in workspace)
- Click:
  ```
  Clean Projects
  ```

👉 This removes old build files and prevents errors

---

## ***🔨 Step 5: Build the Project***

- Again right-click on both both app and stack folder → Click:
  ```
  Build Projects
  ```

👉 Ensure there are **no compilation errors** and wait for **Build Successful**

---

## ***🔌 Step 6: Connect Hardware***

- Connect **CC2650 LaunchPad** via USB
- Ensure:
  - Power LED is ON

---

## ***Step 7: Flash both app and stack folder***

- Right-click project → Click:
  ```
  Flash Project
  ```

## ***Step 8: Download "nrf Connect app" from playstore***

- Press scan and Look for :

   ```
   Comp Strength
   ```

- Observe advertised data:

   ```
   XXXX.XXXX Mpa
   ```


---

# ***5. Firmware Architecture Overview***

The system is based on **TI-RTOS event-driven architecture**, avoiding polling to achieve ultra-low power.

## Key Components

- Task Scheduler → `Task_construct()`
- Timer System → `Util_constructClock()`
- Event Queue → `Queue + Semaphore`
- BLE Stack → GAP + GATT

---

## ***⏱ Timing Configuration***

```c
#define SBP_PERIODIC_EVT_PERIOD 600000   // 10 minutes
#define ADV_ON_DURATION         12000    // 12 sec
#define ADV_OFF_DURATION        300000   // 5 min
```

- Sensor sampling every **10 minutes**
- BLE Advertising 12 sec ON and 5 min OFF  

---

## ***🌡 Temperature Acquisition Logic***

### I²C Read Operation

```c
txBuf[0] = 0x00;   // Temperature register
I2C_transfer(i2c, &i2cTransaction);
```

## Data Conversion

```c
int16_t rawTemp = (rxBuf[0] << 4) | (rxBuf[1] >> 4);

if (rawTemp & 0x0800)
{
    rawTemp |= 0xF000;  // Sign extension
}

float temperature = rawTemp * 0.0625f;
```

✔ Handles negative temperature  
✔ Converts 12-bit data → Celsius  

---

## ***📐 Maturity Calculation Logic***

- Samples collected every 10 min  
- 6 samples → 1 hour average  

```c
Ta = tempAccumulator / 6;
ΔM = (Ta - (-10)) * 1;
cumulativeMaturity += ΔM;
```

---

## ***🧱 Compressive Strength Calculation***

```c
compressiveStrength = A + B * log10f(cumulativeMaturity);
```

Constants:

```c
#define STRENGTH_CONST_A -35.4926f
#define STRENGTH_CONST_B  7.5004f
```

✔ Real-time strength estimation  

---

## ***📡 BLE Advertising Logic***

### Advertising Interval

```c
#define DEFAULT_ADVERTISING_INTERVAL 1600   // 1s
```

### BLE Payload Format

```c
'0','0','0','0','.','0','0','0','0',' ','M','P','a'
```

Example Output:

```
0123.4567 MPa
```

✔ Represents compressive strength  

---


## ***💾 Memory Management***

### SNV Storage

```c
#define SNV_ID_MATURITY  0x82
#define SNV_ID_STRENGTH  0x84
```

### External Flash Logging

- 16-byte structured records  
- SPI-based communication  

```c
Flash_WriteData(addr, data, len);
Flash_ReadData(addr, buffer, len);
```

✔ Reliable long-term storage  

---

## ***⚡ Power Optimization Strategy***

- BLE duty cycling  
- Event-driven RTOS  
- Sensor ON only during read  
- SPI powered dynamically  

```c
SPI_open();
SPI_close();
```

✔ Achieves ultra-low power operation  

---

## ***🔒 Deployment Hold Logic***

```c
deploymentHoldCounter = 12;   // 2 hours
```

- Prevents early incorrect readings  
- Activated after reset  

```c
if (deploymentHoldCounter > 0)
{
    deploymentHoldCounter--;
    return;
}
```

---

## ***🧩 Board Configuration***

Pin mapping defined in:
- CC2650_LAUNCHXL.h 

```c
#define Board_I2C0_SCL0     IOID_1
#define Board_I2C0_SDA0     IOID_0
#define Board_SPI0_MOSI     IOID_9
#define Board_SPI0_MISO     IOID_10
#define Board_SPI0_CLK      IOID_8
#define Board_SPI_FLASH_CS  IOID_11
#define Board_UART_RX       IOID_5 
#define Board_UART_TX       IOID_6
``` 

---

## ***🧪 System Workflow (Actual Execution Flow)***

### Every 10 Minutes

- Wake up  
- Read temperature  
- Store in accumulator  
- Save partial state to SNV  

---

### Every 1 Hour

- Compute average temperature  
- Calculate maturity  
- Update compressive strength  
- Store in flash  
- Update BLE advertisement  

---

# ***6. Troubleshooting***

## Build Errors

- Ensure compiler = **16.9.4.LTS**
- Re-add compiler path in CCS

---

## BLE Not Visible

- Press **Resume (▶)** after debug  
- Check advertising enabled  

---

## Sensor Not Reading

- Verify I²C connections  
- Check address = `0x48`  

---

## Flash Not Working

- Check SPI wiring  
- Verify CS pin mapping  

---
