# 🛒 ICA Shopping – Home Assistant Integration

Sync your ICA shopping lists with Home Assistant and your shopping/todo list in HA.

This also works with Google Keep, which means you can add items to your shopping list
using Google Assistant (voice) and have them automatically synced to your ICA shopping list

## Limitations at the Moment

**Polling Interval (Google Keep):**  
While changes made in Home Assistant are instantly reflected in Google Keep, the reverse is not immediate.  
The integration polls Google Keep for updates every 15 minutes.  
Changes made directly in Google Keep will appear in Home Assistant after the next polling cycle.
[Read more about the limitations here.](https://github.com/watkins-matt/home-assistant-google-keep-sync?tab=readme-ov-file#limitations)

**ICA API:**  
Changes made to your ICA shopping list (e.g. via the ICA app or website) will **not** appear immediately in Home Assistant.  
The integration does **not** support real-time updates, so you’ll need to manually trigger a refresh to fetch the latest version of the list.


## Installation via HACS

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


## How to Get Your `ica_list_id`

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


## Example Automation (ICA Refresh)

Since ICA does not push updates, you can refresh the list every X minutes:

```yaml
automation:
  - alias: "Sync ICA List Every 10 Minutes"
    trigger:
      - platform: time_pattern
        minutes: "/10"
    action:
      - service: ica_shopping.refresh
```

You can also create an automation that refreshes the list when you enter or leave a store.
This only works for ICA stores you've added as zones in Home Assistant.
Purchases made in other locations won't trigger any update.

```yaml
alias: Ica shopping update
description: ""
triggers:
  - trigger: zone
    entity_id: device_tracker.max
    zone: zone.ica
    event: leave
  - trigger: zone
    entity_id: device_tracker.max
    zone: zone.ica
    event: enter
conditions: []
actions:
  - action: ica_shopping.refresh
    data: {}
mode: single

```