import os
from pathlib import Path
import pytest
from movebank_client import MovebankClient


@pytest.fixture
def client_settings():
    return {
        "base_url": "https://www.movebank.mpg.de",
        "username": "fake-admin-user",
        "password": "fake-admin-psw",
        "use_ssl": True,
        "max_http_retries": 10,
        "connect_timeout": 5,
        "data_timeout": 10
    }


@pytest.fixture
def movebank_client(client_settings):
    return MovebankClient(**client_settings)


@pytest.fixture
def mock_movebank_response():
    # Movebank's API doesn't return any content, just 200 OK.
    return ""


@pytest.fixture
def mock_movebank_get_study_response():
    return b'acknowledgements,citation,go_public_date,grants_used,has_quota,i_am_owner,id,is_test,license_terms,license_type,main_location_lat,main_location_long,name,number_of_deployments,number_of_individuals,number_of_tags,principal_investigator_address,principal_investigator_email,principal_investigator_name,study_objective,study_type,suspend_license_terms,i_can_see_data,there_are_data_which_i_cannot_see,i_have_download_access,i_am_collaborator,study_permission,timestamp_first_deployed_location,timestamp_last_deployed_location,number_of_deployed_locations,taxon_ids,sensor_type_ids,contact_person_name\r\n,,,,true,false,1234567890,false,,"CUSTOM",1.1088986592432,23.55,"Test Study",13,13,18,,,"gundi (Gundi)",,"research",false,true,false,true,true,"collaborator",2022-02-12 12:12:12.000,2024-08-15 11:00:22.000,1122334,"test1,test2","GPS,Acceleration","gundi (Gundi)"\r\n'


@pytest.fixture
def mock_movebank_get_individuals_by_study_response():
    return b'birth_hatch_latitude,birth_hatch_longitude,comments,death_comments,earliest_date_born,exact_date_of_birth,group_id,id,latest_date_born,local_identifier,marker_id,mates,mortality_date,mortality_latitude,mortality_longitude,mortality_type,nick_name,offspring,parents,ring_id,sex,siblings,taxon_canonical_name,timestamp_start,timestamp_end,number_of_events,number_of_deployments,sensor_type_ids,taxon_detail\r\n,,,,,,,1234567890,,"Test Individual 1",,,,,,,,,,,,,"test",,,0,0,,\r\n,,,,,,,1234567891,,"Test Individual 2",,,,,,,,,,,,,"test",,,0,0,,\r\n'


@pytest.fixture()
def tag_data_filename():
    return os.path.join(
        Path(os.path.dirname(os.path.realpath(__file__))),
        "test_data/tag_data.json"
    )


@pytest.fixture()
def bad_tag_data_filename():
    return os.path.join(
        Path(os.path.dirname(os.path.realpath(__file__))),
        "test_data/bad_tag_data.json"
    )


@pytest.fixture()
def permissions_filename():
    return os.path.join(
        Path(os.path.dirname(os.path.realpath(__file__))),
        "test_data/permissions.csv"
    )


@pytest.fixture()
def bad_permissions_filename():
    return os.path.join(
        Path(os.path.dirname(os.path.realpath(__file__))),
        "test_data/bad_permissions.csv"
    )
