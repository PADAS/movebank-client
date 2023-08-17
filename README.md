# Movebank Client
## Introduction
The movebank-client is an unofficial async python client to interact with Movebank's API, developed by the Gundi team of [EarthRanger](https://www.earthranger.com/),.

## Installation
pip installmovebank-client

## Usage
```
from movebank_client import MovebankClient

# You can use it as an async context-managed client
async with MovebankClient(
    base_url="https://www.movebank.mpg.de",
    username="your-user",  
    password="your-password",
) as client:
    # Upload permissions for a study
    async with aiofiles.open("permissions.csv", mode='rb') as perm_file:
        await client.post_permissions(
            study_name="your-study",
            csv_file=perm_file
        )

    # Send tag data to a feed
    async with aiofiles.open("data.json", mode='rb') as tag_data:
        await client.post_tag_data(
            feed_name="gundi/earthranger",
            tag_id="your-tag-id",
            json_file=tag_data
        )

# Or create an instance and close the client explicitly later
client = MovebankClient()
# Send tag data to a feed
async with aiofiles.open("data.json", mode='rb') as tag_data:
    await client.post_tag_data(
        feed_name="gundi/earthranger",
        tag_id="your-tag-id",
        json_file=tag_data
    )
...
await client.close()  # Close the session used to send requests
```