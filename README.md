# Movebank Client
## Introduction
The movebank-client is an unofficial async python client to interact with Movebank's API, developed by the Gundi team of [EarthRanger](https://www.earthranger.com/),.

## Installation

```bash
pip install movebank-client
```

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

### Using the CLI suite

There are 3 commands to use directly, in order to test Movebank API
endpoints and credentials:
- `get-events-for-study`: Get Events for a Study
- `get-individual-events`: Get Events for an Individual
- `get-study`: Get a Study, with option to fetch its individuals

For running the CLI suite help, run:

```bash
python cli.py --help
```

For running specific command help, run:

```bash
python cli.py <COMMAND_NAME> --help
```
All responses will be printed in the terminal as JSON or list responses. 

