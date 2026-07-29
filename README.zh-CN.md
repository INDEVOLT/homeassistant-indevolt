<!--
原因：英文 README 已覆盖完整安装和使用流程，但中文用户需要可直接执行的本地化说明。
目标：提供与英文版结构和事实一致、可独立完成安装、升级、回退及自动化配置的简体中文指南。
实现：采用 README.zh-CN.md 的本地化文件名；正文翻译为中文，实际界面标签、配置键、
目录名和文件名保留原文，以便用户对照 Home Assistant 界面和截图操作。
影响：中文用户无需依赖机器翻译即可完成操作；英文 README、现有配置和集成功能均不改变。
边界：不增加英文版未包含的功能承诺、使用说明或设备行为结论。
验证：已逐项核对两份 README 的章节、图片、安装清单、配置参数和升级回退流程。
风险：中英文文件后续可能发生内容漂移，因此修改任一版本时必须同步更新并交叉核对。
回退：该文件是独立说明文件；删除它不会影响英文 README、用户配置或集成运行。
-->

# INDEVOLT Home Assistant 集成

用于监控和控制 [INDEVOLT](https://www.indevolt.com/) 设备的 Home Assistant
自定义集成。

英文版：[README.md](README.md)

## 使用前提

- [ ] 已按照 [Home Assistant 官方安装指南](https://www.home-assistant.io/installation/)
  完成安装。
- [ ] INDEVOLT 设备与 Home Assistant 服务器位于**同一局域网**。
- [ ] INDEVOLT 设备已通电并取得 **IP 地址**。
  - 可在路由器管理列表中查询；
  - 也可在 INDEVOLT App 的设备设置中查看。
- [ ] 已开启 INDEVOLT 设备的 **API 功能**。本集成仅支持 OpenData HTTP 模式。

<img width="800" alt="3http_mode" src="https://github.com/user-attachments/assets/67f8ed96-abb8-4368-b3f3-b2a3484bd4b9" />

- [ ] 确认固件版本满足最低要求。

  | 设备型号 | 最低固件版本 |
  | --- | --- |
  | BK1600/BK1600Ultra | V1.3.0A_R006.072_M4848_00000039 |
  | SolidFlex2000/PowerFlex2000 | CMS: V1406.07.002E |

<img width="400" alt="4fw_version" src="https://github.com/user-attachments/assets/7fb6d58f-9c95-4945-b588-810e68481f5b" />

## 步骤 1：下载 INDEVOLT 集成目录

1. 点击 **Code** > **Download ZIP**。
2. 将 ZIP 文件解压到电脑中。

## 步骤 2：找到 Home Assistant 配置目录

- **Home Assistant OS**：配置目录为 `/config`。
- **Home Assistant Container**：找到 `configuration.yaml` 文件所在的目录，
  该目录即为配置目录。

**提示**：配置目录中应包含 `configuration.yaml` 文件。

```text
配置目录/
└── configuration.yaml
```

## 步骤 3：创建自定义集成目录

1. 进入配置目录。
2. 如果 `custom_components` 目录不存在，请创建该目录。

```text
配置目录/
├── custom_components/
└── configuration.yaml
```

**注意**：所有自定义集成都必须放在 `custom_components` 目录中，否则
Home Assistant 无法识别。

## 步骤 4：添加集成文件

<!--
原因：旧说明容易让用户复制下方安装清单之外的内容，而且清单中的 services.yaml
文件名不准确，可能造成安装结果不一致。
目标：让用户只需按照一份明确的文件清单即可完成安装。
实现：把“排除个别文件”改为“只复制清单中列出的文件”，并纠正 services.yaml 的名称。
影响：安装步骤更明确，可避免无关内容进入集成目录；已有设置和设备不受影响。
边界：这里只调整安装说明和文件清单，不改变集成功能、配置方式或目录位置。
验证：下方清单已与 Home Assistant 安装时需要的文件逐项核对。
-->

1. 在 `custom_components` 目录中创建 `indevolt` 目录。
2. 只将下方清单列出的集成文件复制到 `indevolt` 目录中。不要复制清单中
   未列出的文件或目录。

正确安装后，配置目录应如下所示：

```text
配置目录/
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

## 步骤 5：重启 Home Assistant

1. 在网页界面中选择 **Settings** > **System**。
2. 点击右上角的重启图标。
3. 点击 **Restart Home Assistant**。
4. 点击 **RESTART**。

<img width="1000" alt="5restart_ha" src="https://github.com/user-attachments/assets/1270a590-faf8-43a4-8989-27923d1f3887" />

## 步骤 6：在 Home Assistant 中添加集成

1. 重启后进入网页界面，选择 **Settings** > **Devices & services**。

   <img width="800" alt="" src="https://github.com/user-attachments/assets/f19c8fba-7eec-4994-8fed-4b5a7b2b2d3b" />

2. 点击右下角的 **+ADD INTEGRATION**。

   <img width="150" alt="image" src="https://github.com/user-attachments/assets/9282240e-f408-4ab0-a2ca-e6701994eaee" />

3. 搜索并选择 INDEVOLT 集成。

   <img width="400" alt="" src="https://github.com/user-attachments/assets/836a3d34-d2ad-44c0-87f2-79fc80acd52d" />

4. 填写配置参数：
   - `host`：设备 IP 地址，可通过路由器或 INDEVOLT App 查询。
   - `scan_interval`：数据更新间隔，默认值为 30 秒。

     <img width="300" alt="" src="https://github.com/user-attachments/assets/0a0d38ed-15ed-4072-98bf-c94920d362cb" />

5. 点击 **SUBMIT** 完成安装。
6. 安装后会显示功率模块和电池包。点击 **Skip** 和 **Finish** 完成设置。
   - 每个功率模块最多支持 5 个电池包。
   - 如果没有连接电池包，对应字段将显示为 `None`。
   - 连接电池包后，会显示各电池包的序列号（SN），用于识别不同电池包。

   <img width="300" alt="image" src="https://github.com/user-attachments/assets/f316fa13-44e4-4325-b3a8-09b904b0bd6f" />

## 查看集成

选择 INDEVOLT 集成，即可查看设备和实体信息。

<img width="300" alt="" src="https://github.com/user-attachments/assets/3997f4c9-c146-4c87-9d48-c0970dbe833c" />

<img width="800" alt="" src="https://github.com/user-attachments/assets/c26f0a2c-70ae-456b-9c66-683c2cb52617" />

## 更新集成

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

1. 将现有 `custom_components/indevolt` 目录完整备份到
   `custom_components` 之外，并记录当前安装的版本。
2. 下载新版集成文件，仅使用上方安装目录清单列出的文件整体替换已安装目录。
   不要混用不同版本的文件，也不要复制清单中未列出的内容。
3. 保留现有 INDEVOLT 集成条目、设备和实体。本次更新不需要删除后重新添加集成。
4. 重启 Home Assistant。
5. 确认 INDEVOLT 加载时没有相关错误，并确认原有集成条目、设备和实体仍然存在。

### 回退更新

如果验证失败，请使用完整备份替换 `custom_components/indevolt` 目录，重启
Home Assistant，并确认原有集成条目、设备和实体能够正常加载。

## 创建自动化：设置实时控制

1. 进入 **Settings** > **Automations & scenes**。

   <img width="800" alt="" src="https://github.com/user-attachments/assets/b5bb0b3a-9fce-49ae-b0ce-c9637e69cf9d" />

2. 点击右下角的 **+ Create automation**。

   <img width="800" alt="" src="https://github.com/user-attachments/assets/6c3ed052-eba3-4ae1-b344-4b3c4004eb80" />

3. 选择 **Create new automation**。

   <img width="300" alt="image" src="https://github.com/user-attachments/assets/0dd42045-2eeb-4750-b4a6-d8ada2289b0b" />

4. 点击 **+ Add Trigger**，按需要设置触发条件。

   <img width="500" alt="image" src="https://github.com/user-attachments/assets/2988715f-c0ae-4bac-964e-7d483540120f" />

5. 点击 **+ Add Action**，配置设备操作。
6. 搜索模式，并选择 **Set SolidFlex2000/PowerFlex2000 Work Mode** 作为示例。

   <img width="300" alt="image" src="https://github.com/user-attachments/assets/9b03b0f5-ecbd-43eb-a1f1-e3b82019724f" />

7. 在 **Target** 区域点击 **+ Choose Device**，从列表中选择设备。

   <img width="800" alt="" src="https://github.com/user-attachments/assets/91964bf7-454e-48b3-9064-badb18706489" />

   <img width="300" alt="image" src="https://github.com/user-attachments/assets/6a7b6638-5be3-4749-aed2-f088a73d8fd4" />

8. 在 **Work Mode** 区域选择 **Real-Time Control**，然后按需要设置
   **Status**、**Power** 和 **Target SOC**。

   <img width="300" alt="image" src="https://github.com/user-attachments/assets/bedb1966-513f-4246-b7c4-5f5c579a2e3f" />

   <img width="300" alt="image" src="https://github.com/user-attachments/assets/a6ffeff5-e5c7-45a4-8aa5-5a948ce04b36" />

9. 点击 **Save** 完成自动化设置。

## 常见问题

| 问题描述 | 解决方法 |
| --- | --- |
| 搜索列表中找不到集成 | 确认集成文件位于正确目录：`custom_components/indevolt`。 |
| - 无法添加设备<br>- 无法连接设备<br>- 没有可用数据 | 这通常是由 **HTTP 请求失败** 导致的。<br>1. 确认设备已通电。<br>2. 确认设备 IP 地址正确。<br>3. 在 INDEVOLT App 中检查设备网络状态。<br>4. 确认已满足全部[使用前提](#使用前提)。 |

如果仍然遇到问题，请查看 **Home Assistant 日志**中的详细错误信息。

## 参与贡献

欢迎提供反馈和贡献！你可以提交 Issue 分享建议，也可以提交 Pull Request。
