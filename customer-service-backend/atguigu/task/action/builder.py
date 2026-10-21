import importlib
import inspect
import pkgutil

from atguigu.task.action.base import Action
from atguigu.task.action.builtin.action_listen import ActionListen
from atguigu.task.action.builtin.action_response import ActionResponse
from atguigu.task.action.registry import ActionRegistry
from atguigu.task.action.runner import ActionRunner


def register_custom_actions(runner: ActionRunner) -> None:
    package = importlib.import_module("atguigu.task.action.custom")
    for _, module_name, is_package in pkgutil.iter_modules(
        package.__path__, prefix=f"{package.__name__}."
    ):
        if is_package or module_name.endswith(".shared"):
            continue
        module = importlib.import_module(module_name)
        for _, candidate in inspect.getmembers(module, inspect.isclass):
            if (
                candidate is not Action
                and issubclass(candidate, Action)
                and candidate.__module__ == module.__name__
            ):
                runner.registry.register(candidate())


def build_action_runner() -> ActionRunner:
    runner = ActionRunner(ActionRegistry())
    runner.registry.register(ActionListen())
    runner.registry.register(ActionResponse())
    register_custom_actions(runner)
    return runner
