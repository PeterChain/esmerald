from asyncio import sleep
from typing import TYPE_CHECKING, Any, Dict

from esmerald.applications import ChildEsmerald
from esmerald.injector import Inject
from esmerald.routing.gateways import Gateway
from esmerald.routing.handlers import get
from esmerald.routing.router import Include
from esmerald.routing.views import APIView
from esmerald.testclient import create_client
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

if TYPE_CHECKING:
    from esmerald.requests import Request


def router_first_dependency() -> bool:
    return True


async def router_second_dependency() -> bool:
    await sleep(0.1)
    return False


def controller_first_dependency(headers: Dict[str, Any]) -> dict:
    assert headers
    return dict()


async def controller_second_dependency(request: "Request") -> dict:
    assert request
    await sleep(0.1)
    return dict()


def local_method_first_dependency(query_param: int) -> int:
    assert isinstance(query_param, int)
    return query_param


def local_method_second_dependency(path_param: str) -> str:
    assert isinstance(path_param, str)
    return path_param


test_path = "/test"


class FirstController(APIView):
    path = test_path
    dependencies = {
        "first": Inject(controller_first_dependency),
        "second": Inject(controller_second_dependency),
    }

    @get(
        path="/{path_param:str}",
        dependencies={
            "first": Inject(local_method_first_dependency),
        },
    )
    def test_method(self, first: int, second: dict, third: bool) -> None:
        assert isinstance(first, int)
        assert isinstance(second, dict)
        assert third is False


def test_controller_dependency_injection() -> None:
    with create_client(
        routes=[Gateway(path="/", handler=FirstController)],
        dependencies={
            "second": Inject(router_first_dependency),
            "third": Inject(router_second_dependency),
        },
    ) as client:
        response = client.get(f"{test_path}/abcdef?query_param=12345")
        assert response.status_code == HTTP_200_OK


def xtest_controller_dependency_injection_for_child_esmerald() -> None:
    child = ChildEsmerald(routes=[Gateway(path="/", handler=FirstController)])

    with create_client(
        routes=[Include(app=child)],
        dependencies={
            "second": Inject(router_first_dependency),
            "third": Inject(router_second_dependency),
        },
    ) as client:
        response = client.get(f"{test_path}/abcdef?query_param=12345")
        assert response.status_code == HTTP_200_OK


def test_function_dependency_injection() -> None:
    @get(
        path="/{path_param:str}",
        dependencies={
            "first": Inject(local_method_first_dependency),
            "third": Inject(local_method_second_dependency),
        },
    )
    def test_function(first: int, second: bool, third: str) -> None:
        assert isinstance(first, int)
        assert second is False
        assert isinstance(third, str)

    with create_client(
        routes=[Gateway(path=test_path, handler=test_function)],
        dependencies={
            "first": Inject(router_first_dependency),
            "second": Inject(router_second_dependency),
        },
    ) as client:
        response = client.get(f"{test_path}/abcdef?query_param=12345")
        assert response.status_code == HTTP_200_OK


def test_dependency_isolation() -> None:
    class SecondController(APIView):
        path = "/second"

        @get(path="/")
        def test_method(self, first: dict) -> None:
            pass

    with create_client(
        routes=[
            Gateway(path="/", handler=FirstController),
            Gateway(path="/", handler=SecondController),
        ]
    ) as client:
        response = client.get("/second")
        assert response.status_code == HTTP_400_BAD_REQUEST


def test_dependency_isolation_with_include() -> None:
    class SecondController(APIView):
        path = "/second"

        @get(path="/")
        def test_method(self, first: dict) -> None:
            pass

    with create_client(
        routes=[
            Include(
                routes=[
                    Gateway(path="/", handler=FirstController),
                    Gateway(path="/", handler=SecondController),
                ]
            )
        ]
    ) as client:
        response = client.get("/second")
        assert response.status_code == HTTP_400_BAD_REQUEST


def test_dependency_isolation_with_nested_include() -> None:
    class SecondController(APIView):
        path = "/second"

        @get(path="/")
        def test_method(self, first: dict) -> None:
            pass

    with create_client(
        routes=[
            Include(
                routes=[
                    Include(
                        routes=[
                            Include(
                                routes=[
                                    Include(
                                        routes=[
                                            Include(
                                                routes=[
                                                    Include(
                                                        routes=[
                                                            Gateway(
                                                                path="/",
                                                                handler=FirstController,
                                                            ),
                                                            Gateway(
                                                                path="/",
                                                                handler=SecondController,
                                                            ),
                                                        ]
                                                    )
                                                ]
                                            )
                                        ]
                                    )
                                ]
                            )
                        ]
                    )
                ]
            )
        ],
    ) as client:
        response = client.get("/second")
        assert response.status_code == HTTP_400_BAD_REQUEST
