# ica_shopping

# 🛒 ICA Shopping – Home Assistant Integration

Sync your ICA shopping lists with Home Assistant and your shopping/todo list in HA. Automatically.

## 🔧 Features

- Fetch items from your ICA shopping list
- View them in a Home Assistant sensor
- Automatically sync with todo list in HA - This enables to sync with Google Keep and therefore with Google assitant (voice)
- Two-way smart sync: new items added, removed, or updated
- Avoid duplicates and restore loops


## 📥 Installation

Ensure that you have HACS installed.

Add Integration via HACS:

After you have HACS installed, you can simply click this button:

Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.

Click Download.
Restart Home Assistant.
Alternatively, you can follow these instructions to add it via HACS:

Add Custom Repository:

Open HACS in Home Assistant.
Go to Integrations.
Click on the ... in the top right corner and select Custom repositories.
Add the URL https://github.com/mellamomax/ica_shopping/
Set the category to Integration and click Add.
Install the Integration:

Search for Ica Shopping in the HACS Integrations.
Click Download.
Restart Home Assistant.
Configure Integration:

Go to Settings -> Devices & Services.
Click Add Integration.
Search for and select Ica Shopping.
5. Enter your `session_id` (from ICA.se) and select your shopping list.
6. (Optional) Link a `todo` entity to sync with Google Keep.
Submit

## 🧠 How to Get Your `session_id`

1. Open [ica.se](https://www.ica.se) in Chrome.
2. Log in.
3. Open Developer Tools → Application → Cookies.
4. Find the cookie called `thSessionId`.
5. Copy its value and paste into the integration config.

NOTE: this is only valid for ~3 months which you then need to update


## 🔁 Sync Logic

- ICA → Keep: Items added in ICA appear in Keep
- Keep → ICA: Items added in Keep are synced to ICA
- Items removed in Keep are also removed from ICA
- Recent Keep adds/removes are respected to avoid sync conflicts
- Sensor is updated automatically after every change


## ⏱️ Automation Example

Sync ICA → Keep every 5 minutes:

```yaml
automation:
  - alias: "Sync ICA List Every 5 Minutes"
    trigger:
      - platform: time_pattern
        minutes: "/5"
    action:
      - service: ica_shopping.refresh




---

### 👀 8. Sensor Output
```markdown
## 📊 Sensor Output

The sensor shows:
- Native value: number of items in the ICA list
- Attributes:
  - `list_name`: name of the list
  - `vara_1`, `vara_2`, ...: each individual item as a separate attribute
