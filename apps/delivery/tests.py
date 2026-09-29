from unittest.mock import Mock

import pytest
import requests
from django.test import Client
from django.urls import reverse

from apps.delivery.novaposhta import NovaPoshtaClient, NovaPoshtaError

API_URL = "https://api.example/json/"


def api_answer(data: list[dict], success: bool = True, errors: list[str] | None = None) -> Mock:
    response = Mock()
    response.json.return_value = {"success": success, "data": data, "errors": errors or []}
    return response


@pytest.fixture
def post(monkeypatch) -> Mock:
    mock = Mock()
    monkeypatch.setattr("apps.delivery.novaposhta.requests.post", mock)
    return mock


def test_client_sends_model_and_method_in_body(post: Mock) -> None:
    post.return_value = api_answer(
        [{"Ref": "c1", "Description": "Львів", "AreaDescription": "Львівська"}]
    )

    cities = NovaPoshtaClient("key", API_URL).search_cities("Льв")

    body = post.call_args.kwargs["json"]
    assert body["apiKey"] == "key"
    assert (body["modelName"], body["calledMethod"]) == ("Address", "getCities")
    assert body["methodProperties"]["FindByString"] == "Льв"
    assert cities[0].label == "Львів (Львівська обл.)"


def test_client_keeps_only_requested_kind_of_warehouse(post: Mock) -> None:
    row = {"CityRef": "c1", "CityDescription": "Львів", "Number": "1"}
    post.return_value = api_answer(
        [
            row | {"Ref": "w1", "Description": "Відділення №1", "CategoryOfWarehouse": "Branch"},
            row | {"Ref": "w2", "Description": "Поштомат №2", "CategoryOfWarehouse": "Postomat"},
        ]
    )

    branches = NovaPoshtaClient("key", API_URL).search_warehouses("c1")

    assert [w.ref for w in branches] == ["w1"]


def test_client_raises_when_api_says_no(post: Mock) -> None:
    post.return_value = api_answer([], success=False, errors=["API key is invalid"])

    with pytest.raises(NovaPoshtaError, match="API key is invalid"):
        NovaPoshtaClient("bad", API_URL).search_cities("Київ")


def test_city_not_found_is_an_empty_list(post: Mock) -> None:
    post.return_value = api_answer([], success=False, errors=["FindByString is not specified"])

    assert NovaPoshtaClient("key", API_URL).search_cities("Qqqzz") == []


def test_client_raises_when_network_fails(post: Mock) -> None:
    post.side_effect = requests.ConnectionError("no route")

    with pytest.raises(NovaPoshtaError):
        NovaPoshtaClient("key", API_URL).search_cities("Київ")


def test_client_without_key_does_not_call_api(post: Mock) -> None:
    with pytest.raises(NovaPoshtaError):
        NovaPoshtaClient("", API_URL).search_cities("Київ")
    post.assert_not_called()


def test_city_search_endpoint(client: Client, nova_poshta) -> None:
    response = client.get(reverse("delivery:cities"), {"q": "Ки"})

    assert response.status_code == 200
    assert response.json()["results"][0]["ref"] == "city-kyiv"


def test_city_search_needs_two_letters(client: Client, nova_poshta) -> None:
    assert client.get(reverse("delivery:cities"), {"q": "К"}).json() == {"results": []}


def test_warehouse_search_endpoint_by_type(client: Client, nova_poshta) -> None:
    url = reverse("delivery:warehouses")

    branches = client.get(url, {"city": "city-kyiv"}).json()["results"]
    postomats = client.get(url, {"city": "city-kyiv", "type": "postomat"}).json()["results"]

    assert [w["ref"] for w in branches] == ["wh-1"]
    assert [w["ref"] for w in postomats] == ["wh-5"]


def test_endpoint_answers_503_when_api_is_down(client: Client, nova_poshta) -> None:
    nova_poshta.down = True

    response = client.get(reverse("delivery:cities"), {"q": "Київ"})

    assert response.status_code == 503
