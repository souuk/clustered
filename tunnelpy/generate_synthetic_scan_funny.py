#!/usr/bin/env python3
"""Generate the normal synthetic STM artifacts through needless bureaucracy.

This module is intentionally, theatrically overengineered.  It delegates the
actual scientific work to ``generate_synthetic_scan.py`` so its outputs retain
the same meaning and deterministic values.  Everything around that delegation
exists solely to turn a six-call workflow into an enterprise ceremony.

Use the normal generator for real work.  This file is the funny.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Generic, Iterable, Mapping, Protocol, TypeVar

if __package__:
    from . import generate_synthetic_scan as sane
    from .plot_stm import plot_scan_set
    from .stm_io import ScanSet, load_scan_set
else:
    import generate_synthetic_scan as sane
    from plot_stm import plot_scan_set
    from stm_io import ScanSet, load_scan_set


T = TypeVar("T")
EventHandler = Callable[["CeremonialEvent"], None]


class BureaucraticPhase(Enum):
    """States that a normal function call was apparently too simple to express."""

    UNPETITIONED = auto()
    PETITION_ACCEPTED = auto()
    COMMITTEE_FORMED = auto()
    DEPENDENCIES_NEGOTIATED = auto()
    ARTIFACTS_MANIFESTED = auto()
    RIBBON_CUT = auto()


class ArtifactKind(Enum):
    FORWARD_BINARY = auto()
    BACKWARD_BINARY = auto()
    PARAMETERS = auto()
    PREVIEW = auto()
    NOTICE = auto()
    RAW_MATRIX_FIGURE = auto()
    SCHEMA_FIGURE = auto()
    FOUR_PANEL_FIGURE = auto()


@dataclass(frozen=True)
class CeremonialEvent:
    sequence: int
    topic: str
    message: str


class EventBus:
    """A publish/subscribe system for print statements."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._sequence = 0

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        self._handlers[topic].append(handler)

    def publish(self, topic: str, message: str) -> None:
        self._sequence += 1
        event = CeremonialEvent(self._sequence, topic, message)
        for handler in (*self._handlers.get(topic, ()), *self._handlers.get("*", ())):
            handler(event)


@dataclass(frozen=True)
class InvocationCovenant:
    data_dir: Path
    raw_matrix_figure: Path
    schema_figure: Path
    four_panel_figure: Path
    ritual_token: str
    ceremony_acknowledged: bool

    def submit_for_notarization(self) -> None:
        if not self.ceremony_acknowledged:
            raise RuntimeError("The needless ceremony was not acknowledged.")
        if self.ritual_token != "Q-IS-NOT-HEIGHT":
            raise RuntimeError("The ritual token is scientifically incorrect.")
        destinations = (
            self.data_dir,
            self.raw_matrix_figure.parent,
            self.schema_figure.parent,
            self.four_panel_figure.parent,
        )
        if any(not str(destination) for destination in destinations):
            raise RuntimeError("A destination escaped the paperwork.")


@dataclass(frozen=True)
class ArtifactReceipt(Generic[T]):
    kind: ArtifactKind
    value: T
    issued_by: str


class ArtifactLedger:
    """A type-adjacent dictionary wearing a tie."""

    def __init__(self) -> None:
        self._receipts: dict[ArtifactKind, ArtifactReceipt[Any]] = {}

    def file(self, receipt: ArtifactReceipt[Any]) -> None:
        if receipt.kind in self._receipts:
            raise RuntimeError(f"Duplicate paperwork for {receipt.kind.name}")
        self._receipts[receipt.kind] = receipt

    def retrieve(self, kind: ArtifactKind, expected_type: type[T]) -> T:
        try:
            value = self._receipts[kind].value
        except KeyError as exc:
            raise RuntimeError(f"Artifact {kind.name} lacks Form 27-B") from exc
        if not isinstance(value, expected_type):
            raise TypeError(
                f"Artifact {kind.name} is {type(value).__name__}, "
                f"not {expected_type.__name__}"
            )
        return value

    def paths(self) -> tuple[Path, ...]:
        return tuple(
            receipt.value
            for receipt in self._receipts.values()
            if isinstance(receipt.value, Path)
        )


@dataclass
class CommitteeContext:
    covenant: InvocationCovenant
    bus: EventBus
    ledger: ArtifactLedger = field(default_factory=ArtifactLedger)
    scan: ScanSet | None = None
    phase: BureaucraticPhase = BureaucraticPhase.UNPETITIONED

    def transition(
        self,
        expected: BureaucraticPhase,
        destination: BureaucraticPhase,
    ) -> None:
        if self.phase is not expected:
            raise RuntimeError(
                f"Committee attempted {self.phase.name} -> {destination.name}; "
                f"Form 12 expected {expected.name}"
            )
        self.bus.publish(
            "phase",
            f"{self.phase.name.replace('_', ' ').title()} -> "
            f"{destination.name.replace('_', ' ').title()}",
        )
        self.phase = destination


class WorkOrder(Protocol):
    name: str
    dependencies: frozenset[str]

    def execute(self, context: CommitteeContext) -> None:
        ...


@dataclass(frozen=True)
class CallableWorkOrder:
    name: str
    dependencies: frozenset[str]
    operation: Callable[[CommitteeContext], None]

    def execute(self, context: CommitteeContext) -> None:
        context.bus.publish("work", f"Opening work order: {self.name}")
        self.operation(context)
        context.bus.publish("work", f"Stamping work order complete: {self.name}")


class DependencyNegotiationCouncil:
    """Topologically sorts six ordinary function calls, with minutes."""

    def __init__(self, orders: Iterable[WorkOrder]) -> None:
        self._orders = {order.name: order for order in orders}

    def ratify(self) -> tuple[WorkOrder, ...]:
        approved: list[WorkOrder] = []
        remaining = dict(self._orders)
        completed: set[str] = set()
        while remaining:
            eligible = sorted(
                name
                for name, order in remaining.items()
                if order.dependencies <= completed
            )
            if not eligible:
                unresolved = {
                    name: sorted(order.dependencies - completed)
                    for name, order in remaining.items()
                }
                raise RuntimeError(f"Committee deadlock: {unresolved}")
            for name in eligible:
                approved.append(remaining.pop(name))
                completed.add(name)
        return tuple(approved)


class RedundantFacadeFactory:
    """Constructs commands that could have been written directly in ``main``."""

    @staticmethod
    def _file_scan(context: CommitteeContext) -> None:
        forward, backward, parameters, preview = sane.write_scan(
            context.covenant.data_dir
        )
        for kind, path in (
            (ArtifactKind.FORWARD_BINARY, forward),
            (ArtifactKind.BACKWARD_BINARY, backward),
            (ArtifactKind.PARAMETERS, parameters),
            (ArtifactKind.PREVIEW, preview),
        ):
            context.ledger.file(ArtifactReceipt(kind, path, "Binary Committee"))

    @staticmethod
    def _file_notice(context: CommitteeContext) -> None:
        path = sane.write_notice(context.covenant.data_dir)
        context.ledger.file(
            ArtifactReceipt(ArtifactKind.NOTICE, path, "Disclosure Subcommittee")
        )

    @staticmethod
    def _render_raw_matrix(context: CommitteeContext) -> None:
        path = sane.render_raw_to_matrix(
            context.covenant.data_dir,
            context.covenant.raw_matrix_figure,
        )
        context.ledger.file(
            ArtifactReceipt(
                ArtifactKind.RAW_MATRIX_FIGURE,
                path,
                "Pixel Appropriations Board",
            )
        )

    @staticmethod
    def _render_schema(context: CommitteeContext) -> None:
        path = sane.render_file_schema_check(
            context.covenant.data_dir,
            context.covenant.schema_figure,
        )
        context.ledger.file(
            ArtifactReceipt(
                ArtifactKind.SCHEMA_FIGURE,
                path,
                "Schema Compliance Tribunal",
            )
        )

    @staticmethod
    def _load_scan(context: CommitteeContext) -> None:
        context.scan = load_scan_set(
            context.covenant.data_dir,
            prefix=sane.PREFIX,
            scan_number=sane.SCAN_NUMBER,
        )

    @staticmethod
    def _render_four_panel(context: CommitteeContext) -> None:
        if context.scan is None:
            raise RuntimeError("The scan was not blessed by the Loading Council.")
        path = plot_scan_set(
            context.scan,
            context.covenant.four_panel_figure,
            level="none",
            robust_limits=True,
            dpi=240,
        )
        context.ledger.file(
            ArtifactReceipt(
                ArtifactKind.FOUR_PANEL_FIGURE,
                path,
                "Four-Panel Directorate",
            )
        )

    @classmethod
    def establish_work_orders(cls) -> tuple[WorkOrder, ...]:
        return (
            CallableWorkOrder("01-file-scan", frozenset(), cls._file_scan),
            CallableWorkOrder(
                "02-file-notice",
                frozenset({"01-file-scan"}),
                cls._file_notice,
            ),
            CallableWorkOrder(
                "03-render-raw-matrix",
                frozenset({"01-file-scan"}),
                cls._render_raw_matrix,
            ),
            CallableWorkOrder(
                "04-render-schema",
                frozenset({"01-file-scan"}),
                cls._render_schema,
            ),
            CallableWorkOrder(
                "05-load-scan",
                frozenset({"01-file-scan"}),
                cls._load_scan,
            ),
            CallableWorkOrder(
                "06-render-four-panel",
                frozenset({"05-load-scan"}),
                cls._render_four_panel,
            ),
        )


class MinistryOfSyntheticImageGeneration:
    """The final abstraction layer between the user and six function calls."""

    def __init__(self, covenant: InvocationCovenant, verbose: bool) -> None:
        bus = EventBus()
        if verbose:
            bus.subscribe(
                "*",
                lambda event: print(
                    f"[minutes {event.sequence:02d}] "
                    f"{event.topic.upper()}: {event.message}"
                ),
            )
        self._context = CommitteeContext(covenant=covenant, bus=bus)

    def convene(self) -> ArtifactLedger:
        context = self._context
        context.covenant.submit_for_notarization()
        context.transition(
            BureaucraticPhase.UNPETITIONED,
            BureaucraticPhase.PETITION_ACCEPTED,
        )
        orders = RedundantFacadeFactory.establish_work_orders()
        context.transition(
            BureaucraticPhase.PETITION_ACCEPTED,
            BureaucraticPhase.COMMITTEE_FORMED,
        )
        agenda = DependencyNegotiationCouncil(orders).ratify()
        context.transition(
            BureaucraticPhase.COMMITTEE_FORMED,
            BureaucraticPhase.DEPENDENCIES_NEGOTIATED,
        )
        for order in agenda:
            order.execute(context)
        context.transition(
            BureaucraticPhase.DEPENDENCIES_NEGOTIATED,
            BureaucraticPhase.ARTIFACTS_MANIFESTED,
        )
        context.transition(
            BureaucraticPhase.ARTIFACTS_MANIFESTED,
            BureaucraticPhase.RIBBON_CUT,
        )
        return context.ledger


def _attach_final_forms(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--data-dir", type=Path, default=Path("synthetic_data"))
    parser.add_argument(
        "--figure",
        type=Path,
        default=Path("poster/raw-data-to-matrix.png"),
    )
    parser.add_argument(
        "--schema-figure",
        type=Path,
        default=Path("poster/file-schema-validation.png"),
    )
    parser.add_argument(
        "--four-panel",
        type=Path,
        default=Path("poster/synthetic-q-four-panel.png"),
    )
    parser.add_argument(
        "--ritual-token",
        required=True,
        choices=("Q-IS-NOT-HEIGHT",),
        help="mandatory scientific password",
    )
    parser.add_argument(
        "--i-accept-the-needless-ceremony",
        required=True,
        action="store_true",
        help="mandatory acknowledgement that this could have been simple",
    )
    parser.add_argument(
        "--publish-committee-minutes",
        action="store_true",
        help="print the internal bureaucracy while it happens",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "The funny: generate the normal synthetic images through a "
            "deliberately chaotic command structure."
        )
    )
    please = parser.add_subparsers(dest="courtesy", required=True).add_parser(
        "please"
    )
    generate = please.add_subparsers(dest="request", required=True).add_parser(
        "generate"
    )
    the = generate.add_subparsers(dest="article", required=True).add_parser("the")
    images = the.add_subparsers(dest="object", required=True).add_parser("images")
    _attach_final_forms(images)
    return parser


def _covenant_from_namespace(args: argparse.Namespace) -> InvocationCovenant:
    ceremonial_words: Mapping[str, str] = {
        "courtesy": "please",
        "request": "generate",
        "article": "the",
        "object": "images",
    }
    for field_name, expected in ceremonial_words.items():
        if getattr(args, field_name) != expected:
            raise RuntimeError(f"The ceremonial phrase lost its {field_name}.")
    return InvocationCovenant(
        data_dir=args.data_dir,
        raw_matrix_figure=args.figure,
        schema_figure=args.schema_figure,
        four_panel_figure=args.four_panel,
        ritual_token=args.ritual_token,
        ceremony_acknowledged=args.i_accept_the_needless_ceremony,
    )


def main() -> None:
    args = build_parser().parse_args()
    covenant = _covenant_from_namespace(args)
    ledger = MinistryOfSyntheticImageGeneration(
        covenant,
        verbose=args.publish_committee_minutes,
    ).convene()
    print("The committee generated:")
    for path in ledger.paths():
        print(f"  {path.resolve()}")
    print("All forms approved. This was absolutely worth seven abstraction layers.")


if __name__ == "__main__":
    main()
