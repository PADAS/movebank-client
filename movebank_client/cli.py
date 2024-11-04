import asyncclick as click
import json

from dateparser import parse as dp
from datetime import datetime, timezone, timedelta
from client import MovebankClient


@click.group(help="A group of commands for getting data from Movebank account")
def cli():
    pass


common_options = [
    click.option('--username', help='Movebank username', required=True),
    click.option('--password', help='Movebank password', required=True),
]


def add_options(options):
    def _add_options(func):
        for option in reversed(options):
            func = option(func)
        return func

    return _add_options


@cli.command(help="Get a Study, with option to fetch its individuals")
@add_options(common_options)
@click.option('--study_id', '-s', help='Study ID', required=True)
@click.option('--list-individuals', '-l', help='List all individuals', is_flag=True, default=False)
async def get_study(username: str, password: str, study_id: str, list_individuals: bool):
    async with MovebankClient(username=username, password=password) as client:
        study = await client.get_study(study_id=study_id)

        print("Study:\n")
        print(json.dumps(study, indent=2) + "\n")

        if list_individuals:
            individuals = [individual for individual in await client.get_individuals_by_study(study_id=study_id)]

            print("Individuals:\n")

            for individual in individuals:
                if individual["timestamp_end"]:
                    timestamp_end = dp(individual["timestamp_end"])
                    timestamp_end = timestamp_end.replace(tzinfo=timezone.utc)
                    ended = (datetime.now(tz=timezone.utc) - timedelta(days=7)) > timestamp_end
                else:
                    ended = False
                print(
                    f'{individual["id"]}: {individual["nick_name"]}, {individual["local_identifier"]}, {individual["nick_name"]}, {individual["ring_id"]}, {individual["timestamp_end"]}, {ended}\n'
                )


@cli.command(help="Get Events for a Study")
@add_options(common_options)
@click.option('--study_id', '-s', help='Study ID', required=True)
async def get_events_for_study(username, password, study_id):
    async with MovebankClient(username=username, password=password) as client:

        individuals = [individual for individual in await client.get_individuals_by_study(study_id=study_id)]

        print("Individuals:\n")

        for individual in individuals:
            if individual["timestamp_end"]:
                timestamp_end = dp(individual["timestamp_end"])
                timestamp_end = timestamp_end.replace(tzinfo=timezone.utc)
                ended = (datetime.now(tz=timezone.utc) - timedelta(days=7)) > timestamp_end
            else:
                ended = False
            print(
                f'{individual["id"]}: {individual["nick_name"]}, {individual["local_identifier"]}, {individual["nick_name"]}, {individual["ring_id"]}, {individual["timestamp_end"]}, {ended}\n'
            )

        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=1)

        async def get_events():
            for individual in individuals:
                print(f'Getting events for individual: {individual["id"]}')
                async for item in client.get_individual_events_by_time(study_id=study_id, individual_id=individual["id"],
                                                                       timestamp_start=start, timestamp_end=end):
                    print(item)

        await get_events()


@cli.command(help="Get Events for an Individual")
@add_options(common_options)
@click.option('--study_id', '-s', help='Study ID', required=True)
@click.option('--individual_id', '-i', help='Individual ID', required=True)
async def get_individual_events(username, password, study_id, individual_id):
    async with MovebankClient(username=username, password=password) as client:
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=1)


        items = [
            item async for item in client.get_individual_events_by_time(
                study_id=study_id, 
                individual_id=individual_id, 
                timestamp_start=start,
                timestamp_end=end
            )
        ]


        print("Events:\n")

        for item in items:
            print(json.dumps(item, indent=2) + "\n")


if __name__ == '__main__':
    cli()