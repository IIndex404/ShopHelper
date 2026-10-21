"""把 YAML 配置加载并校验为流程对象。"""

from pathlib import Path
from typing import Any

import yaml

from atguigu.task.flow.flows import Flow, FlowSlot, FlowsList
from atguigu.task.flow.steps import CollectFlowStep, EndFlowStep, FlowStep


class FlowLoader:
    def load_many(self, paths: list[Path]) -> FlowsList:
        flows: list[Flow] = []
        slots: dict[str, FlowSlot] = {}
        seen_flow_ids: set[str] = set()

        for path in paths:
            loaded = self.load(path)
            duplicate_slots = set(slots).intersection(loaded.slots)
            if duplicate_slots:
                names = ", ".join(sorted(duplicate_slots))
                raise ValueError(f"流程配置中存在重复槽位: {names}")
            duplicate_flows = seen_flow_ids.intersection(flow.id for flow in loaded.flows)
            if duplicate_flows:
                names = ", ".join(sorted(duplicate_flows))
                raise ValueError(f"流程配置中存在重复流程: {names}")
            slots.update(loaded.slots)
            flows.extend(loaded.flows)
            seen_flow_ids.update(flow.id for flow in loaded.flows)

        return FlowsList(flows=flows, slots=slots)

    def load(self, path: Path) -> FlowsList:
        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{path} 的顶层必须是映射")
        slots = self._load_slots(data.get("slots", {}))
        flows = self._load_flows(data.get("flows", {}), slots)
        return FlowsList(flows=flows, slots=slots)

    @staticmethod
    def _load_slots(data: dict[str, Any]) -> dict[str, FlowSlot]:
        return {
            name: FlowSlot(name=name, **(definition or {}))
            for name, definition in data.items()
        }

    def _load_flows(
        self,
        data: dict[str, Any],
        slot_definitions: dict[str, FlowSlot],
    ) -> list[Flow]:
        flows: list[Flow] = []
        for flow_id, definition in data.items():
            steps = [FlowStep.from_dict(raw) for raw in definition.get("steps", [])]
            flow = Flow(
                id=flow_id,
                name=definition.get("name"),
                description=definition.get("description", ""),
                steps=steps,
                slots=self._collect_flow_slots(slot_definitions, steps),
            )
            self._validate_flow(flow)
            flows.append(flow)
        return flows

    @staticmethod
    def _collect_flow_slots(
        slot_definitions: dict[str, FlowSlot],
        steps: list[FlowStep],
    ) -> list[FlowSlot]:
        result: list[FlowSlot] = []
        seen: set[str] = set()
        for step in steps:
            if not isinstance(step, CollectFlowStep) or step.slot_name in seen:
                continue
            slot = slot_definitions.get(step.slot_name)
            if slot is None:
                raise ValueError(f"collect 步骤引用了未定义槽位: {step.slot_name}")
            seen.add(step.slot_name)
            result.append(slot)
        return result

    @staticmethod
    def _validate_flow(flow: Flow) -> None:
        ids = [step.id for step in flow.steps]
        if len(ids) != len(set(ids)):
            raise ValueError(f"流程 {flow.id} 中 step id 重复")
        if flow.start_step() is None:
            raise ValueError(f"流程 {flow.id} 缺少 start 步骤")
        if not any(isinstance(step, EndFlowStep) for step in flow.steps):
            raise ValueError(f"流程 {flow.id} 缺少 end 步骤")
        known = set(ids)
        for step in flow.steps:
            for link in step.next:
                if link.target not in known:
                    raise ValueError(
                        f"流程 {flow.id} 的步骤 {step.id} 指向不存在的 {link.target}"
                    )
