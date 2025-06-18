# ica_shopping

# 🛒 ICA Shopping – Home Assistant Integration

Sync your ICA shopping lists with Home Assistant and your shopping/todo list in HA. Automatically.

## 🔧 Features

- Fetch items from your ICA shopping list
- View them in a Home Assistant sensor
- Automatically sync with todo list in HA - This enables to sync with Google Keep and therefore with Google assitant (voice)
- Two-way smart sync: new items added, removed, or updated
- Avoid duplicates and restore loops

NOTE: Integration is under construction and will have bugs or not work at all.
Will keep updating this. Feel free to add issues and or suggest features


## 📥 Installation via HACS

Add Custom Repository:

Open HACS in Home Assistant.
Click on the ... in the top right corner and select Custom repositories.
Add the URL https://github.com/mellamomax/ica_shopping/
Set the category to Integration and click Add.
Download the Integration and restart Home Assistant.

Configure Integration:

Go to Settings -> Devices & Services.
Click Add Integration.
Search for and select Ica Shopping.
5. Enter your `session_id` and `ica_list_id` which you want to add.
6. (Optional) Link a `todo` entity to sync with Google Keep.
Submit

## How to Get Your `session_id`

1. Open [ica.se](https://www.ica.se) in Chrome.
2. Log in.
3. Open Developer Tools → Application → Cookies.
4. Find the cookie called `thSessionId`.
5. Copy its value and paste into the integration config.

NOTE: this is only valid for ~3 months which you then need to update


## How to Get Your `ica_list_id

1. Open [ica.se](https://www.ica.se) in Chrome
2. Log in
3. Go to one of your shopping list or create a new
4. Open Developer Tools → Network.
5. Make a change in your list
6. Under Network it will now show the request made for your list with your list ID
7. Copy its value and paste into the integration config.

The url looks like this:
https://apimgw-pub.ica.se/sverige/digx/shopping-list/v1/api/row/ab95586e-ffd3-4927-bfc7-85d1c5193dbb
with 'ab95586e-ffd3-4927-bfc7-85d1c5193dbb' being your list_id


## Sync Logic

- ICA → Keep: Items added in ICA appear in Keep
- Keep → ICA: Items added in Keep are synced to ICA
- Items removed in Keep are also removed from ICA
- Recent Keep adds/removes are respected to avoid sync conflicts
- Sensor is updated automatically after every change


## Automation Example - Dont know if theres a polling limit right now. use with causion

Sync ICA → Keep every 5 minutes:

```yaml
automation:
  - alias: "Sync ICA List Every 5 Minutes"
    trigger:
      - platform: time_pattern
        minutes: "/5"
    action:
      - service: ica_shopping.refresh
```



## Sensor Output

The sensor shows:
- Native value: number of items in the ICA list
- Attributes:
  - `list_name`: name of the list
  - `vara_1`, `vara_2`, ...: each individual item as a separate attribute
