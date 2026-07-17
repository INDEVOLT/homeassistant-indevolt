# Indevolt integration for Home Assistant

A Home Assistant custom integration to monitor and control [Indevolt](https://www.indevolt.com/) devices.


## Prerequisites
- [ ] Home Assistant has been installed according to the [official installation guide](https://www.home-assistant.io/installation/).
- [ ] The Indevolt device and Home Assistant server are on the **same local network**.
- [ ] The Indevolt device is powered on and has obtained an **IP address**.
  - Query via router’s management list;
  - Check in INDEVOLT App device settings;
- [ ] Ensure that the Indevolt device **API function is enabled**. This integration only supports OpenData HTTP mode.
<img width="800" alt="3http_mode" src="https://github.com/user-attachments/assets/67f8ed96-abb8-4368-b3f3-b2a3484bd4b9" />

- [ ] Confirm the firmware version meets the minimum requirement.

  | Model                       | Minimum Firmware Version        |
  | --------------------------- | ------------------------------- |
  | BK1600/BK1600Ultra          | V1.3.0A_R006.072_M4848_00000039 |
  | SolidFlex2000/PowerFlex2000 | CMS: V1406.07.002E |

<img width="400" alt="4fw_version" src="https://github.com/user-attachments/assets/7fb6d58f-9c95-4945-b588-810e68481f5b" />


## Step 1: Download the indevolt integration folder

1. Click **Code** > **Download ZIP**.
2. Unzip the ZIP file to your computer.


## Step 2: Locate the HA configuration directory path

- **Home Assistant OS**: The configuration directory is located in `/config`.
- **Home Assistant Container**: You can access the configuration directory by locating the `configuration.yaml` file.

**Tip**: The directory should contain a `configuration.yaml` file.

```
config directory/
└── configuration.yaml
```

## Step 3: Create a custom integration directory

1. Enter the config directory.
2. Create the `custom_components` directory if it does not exist.

```
config directory/
├── custom_components/
└── configuration.yaml
```

**Note**: All custom integrations must be placed under `custom_components`, otherwise HA will not be able to recognize them.


## Step 4: Add the integration files

<!--
原因：旧说明容易让用户复制下方安装清单之外的内容，而且清单中的 services.yaml
文件名不准确，可能造成安装结果不一致。
目标：让用户只需按照一份明确的文件清单即可完成安装。
实现：把“排除个别文件”改为“只复制清单中列出的文件”，并纠正 services.yaml 的名称。
影响：安装步骤更明确，可避免无关内容进入集成目录；已有设置和设备不受影响。
边界：这里只调整安装说明和文件清单，不改变集成功能、配置方式或目录位置。
验证：下方清单已与 Home Assistant 安装时需要的文件逐项核对。
-->

1. Create the `indevolt` directory in the config directory.
2. Copy only the integration files shown below into the `indevolt` directory.
   Do not copy files or folders that are not shown in this list.

Once installed correctly, your configuration directory should look like this:

```
config directory/
└── custom_components/
    └── indevolt/
        ├── __init__.py
        ├── config_flow.py
        ├── const.py
        ├── coordinator.py
        ├── entity.py
        ├── indevolt_api.py
        ├── manifest.json
        ├── number.py
        ├── select.py
        ├── sensor.py
        ├── services.yaml
        ├── switch.py
```

## Step 5: Restart Home Assistant

1. Select **Settings** > **System** in the web interface.
2. Click the restart icon in the upper right corner.
3. Click **Restart Home Assistant**.
4. Click **RESTART**.

<img width="1000" alt="5restart_ha" src="https://github.com/user-attachments/assets/1270a590-faf8-43a4-8989-27923d1f3887" />


## Step 6: Add integration to Home Assistant

1. After restarting, enter the web interface and select **Settings** > **Devices & services**.
    <img width="800" alt="" src="https://github.com/user-attachments/assets/f19c8fba-7eec-4994-8fed-4b5a7b2b2d3b" />


2. Click **+ADD INTEGRATION** in the lower right corner.  
   <img width="150" alt="image" src="https://github.com/user-attachments/assets/9282240e-f408-4ab0-a2ca-e6701994eaee" />

3. Search for integration INDEVOLT.  
    <img width="400" alt="" src="https://github.com/user-attachments/assets/836a3d34-d2ad-44c0-87f2-79fc80acd52d" />

4. Configuration parameters:
   - `host`: Device IP address, which can be obtained by checking the router/app.
   - `scan_interval`: Used to control the frequency of data updates, default is 30 seconds.  

     <img width="300" alt="" src="https://github.com/user-attachments/assets/0a0d38ed-15ed-4072-98bf-c94920d362cb" />

5. Click **SUBMIT** to finish the installation.
6. The power module and battery packs will be displayed after installation. Click Skip and Finish to complete the setup process.
    - Each power module supports up to 5 battery packs.
    - If no battery pack is connected, the corresponding field will be shown as None.
    - When battery packs are connected, the serial number (SN) of each battery pack will be displayed for identification.  
    <img width="300" alt="image" src="https://github.com/user-attachments/assets/f316fa13-44e4-4325-b3a8-09b904b0bd6f" />


## View Integration

Select the INDEVOLT integration to display the device and entity information.

<img width="300" alt="" src="https://github.com/user-attachments/assets/3997f4c9-c146-4c87-9d48-c0970dbe833c" />

<img width="800" alt="" src="https://github.com/user-attachments/assets/c26f0a2c-70ae-456b-9c66-683c2cb52617" />




## Update integration

<!--
原因：旧升级说明要求删除并重新添加集成，可能导致设备、实体名称和自动化引用变化。
目标：提供无需重建设备且能够恢复旧版本的升级路径。
实现：升级前完整备份旧目录，整体替换集成文件，保留现有集成条目，重启后核对原设备和实体。
影响：升级失败时可以整体恢复旧目录；正常升级不需要重建设备，也不改变配置格式。
边界：不迁移用户数据、不修改现有实体标识，也不自动删除任何配置。
验证：升级后可通过 Home Assistant 界面确认原有集成条目、设备和实体仍然存在。
风险：混用新旧版本文件可能导致集成无法正常加载，因此必须整体替换集成目录。
回退：恢复完整备份目录并重启 Home Assistant，再确认原有集成、设备和实体正常显示。
-->

1. Back up the entire existing `custom_components/indevolt` directory outside
   `custom_components`, and record the currently installed version.
2. Download the new integration files and replace the installed directory with
   only the integration files shown in the installation tree above. Do not mix
   files from different versions or copy anything that is not listed.
3. Keep the existing INDEVOLT integration entry, devices, and entities. This
   update does not require deleting or adding the entry again.
4. Restart Home Assistant.
5. Confirm that INDEVOLT loads without related errors and that the existing
   integration entry, devices, and entities are still present.

### Roll back an update

If validation fails, replace the entire `custom_components/indevolt` directory
with the backup, restart Home Assistant, and confirm that the original
integration entry, devices, and entities load normally.


## Create Automation: Set Real-Time Control

1. Go to **Settings** > **Automations & scenes**.
    <img width="800" alt="" src="https://github.com/user-attachments/assets/b5bb0b3a-9fce-49ae-b0ce-c9637e69cf9d" />

2. Click the button in the lower right corner **+ Create automation**.
    <img width="800" alt="" src="https://github.com/user-attachments/assets/6c3ed052-eba3-4ae1-b344-4b3c4004eb80" />

3. Select **Create new automation**.  
   <img width="300" alt="image" src="https://github.com/user-attachments/assets/0dd42045-2eeb-4750-b4a6-d8ada2289b0b" />

4. Click **+ Add Trigger** and configure the trigger event based on your requirements.  
   <img width="500" alt="image" src="https://github.com/user-attachments/assets/2988715f-c0ae-4bac-964e-7d483540120f" />

5. Click **+ Add Action** to configure the device action.
6. Search for mode and select Set SolidFlex2000/PowerFlex2000 Work Mode (as an example).  
   <img width="300" alt="image" src="https://github.com/user-attachments/assets/9b03b0f5-ecbd-43eb-a1f1-e3b82019724f" />

7. In the **Target** section, click **+ Choose Device** and select your device from the list.  
    <img width="800" alt="" src="https://github.com/user-attachments/assets/91964bf7-454e-48b3-9064-badb18706489" />
    <img width="300" alt="image" src="https://github.com/user-attachments/assets/6a7b6638-5be3-4749-aed2-f088a73d8fd4" />


8. In the **Work Mode** section, choose **Real-Time Control**, then configure **Status**, **Power**, and **Target SOC** as needed.  
    <img width="300" alt="image" src="https://github.com/user-attachments/assets/bedb1966-513f-4246-b7c4-5f5c579a2e3f" />
    <img width="300" alt="image" src="https://github.com/user-attachments/assets/a6ffeff5-e5c7-45a4-8aa5-5a948ce04b36" />

9. Click **Save** to complete the automation setup.

## FAQ

| Problem Description | Solutions |
| ------------------- | ----------|
| Integration not found in search list | Verify the integration file is located in the correct folder: `custom_components/indevolt`. |
| - Unable to add  device. <br> - Unable to connect to the device.  <br> - No data available   | This is typically caused by an **HTTP request failure**. <br>  1.  Verify the device is powered on.<br> 2. Confirm the device's IP address is correct.<br> 3. Check the device's network status in Indevolt app.<br>4. Ensure you have met all the [prerequisites](#prerequisites). |

If you encounter any issues, please check the **Home Assistant logs** for detailed error messages.

## Contribute

We welcome your feedback and contributions! Please feel free to open an issue with your suggestions or submit a pull request.
