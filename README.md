# buld_site_creator
Simple script to bulk create sites in the mist dashboard from CSV file.

## Prerequisits:
- config.py should have the `google_api_key` value filled out.
- google_api_key should have the google maps `Geocoding` and `Timezone` APIs allowed
- CSV with the following fields `site_name`, `site_address` with option fields `rf_template_name`

## Usage:

```bash
python ./site_creator.py -k <Mist API Key> -o <Mist Org ID>
```


