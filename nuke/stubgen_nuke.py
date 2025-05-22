import argparse
import builtins
import inspect
import itertools
import shutil
import sys
from pathlib import Path

import mypy.fastparse
import mypy.moduleinspect
import mypy.stubgen
import mypy.stubgenc
import mypy.stubutil
from mypy.stubgenc import DocstringSignatureGenerator, SignatureGenerator

import nuke
from stubgenlib.siggen import (
    AdvancedSigMatcher,
    AdvancedSignatureGenerator,
)


class ModuleInspect:
    """
    Patch ModuleInspect so that it imports modules directly into the current process rather than
    using a multiprocessing.
    """

    def get_package_properties(
        self, package_id: str
    ) -> mypy.moduleinspect.ModuleProperties:
        return mypy.moduleinspect.get_package_properties(package_id)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return


class NukeSignatureGenerator(AdvancedSignatureGenerator):
    sig_matcher = AdvancedSigMatcher(
        # signature_overrides={
        #     # signatures for these special methods include many inaccurate overloads
        #     "*.__ne__": "(self, other: object) -> bool",
        #     "*.__eq__": "(self, other: object) -> bool",
        # },
        # arg_type_overrides={
        #     ("*", "parts", "list"): "Iterable[Part]",
        #     ("*", "channels", "dict"): "Mapping[str, Channel | numpy.ndarray]",
        # },
        # result_type_overrides={
        #     ("*.isOpenExrFile", "*"): "bool",
        #     ("*.isComplete", "*"): "bool",
        #     ("*.File.__enter__", "object"): "Self",
        # },
        # property_type_overrides={
        #     ("*.File.parts", "*"): "list[Part]",
        # },
    )


class InspectionStubGenerator(mypy.stubgenc.InspectionStubGenerator):
    _REAL_BUILTINS = set([x[0] for x in inspect.getmembers(builtins)])

    _MODULE_REMAP = {
        "gsv": "_gsv",
        "_linkableKnobInfo": "_nuke",
    }

    def get_sig_generators(self) -> list[SignatureGenerator]:
        return [
            NukeSignatureGenerator(
                fallback_sig_gen=DocstringSignatureGenerator(),
            )
        ]

    def get_obj_module(self, obj: object) -> str | None:
        module = super().get_obj_module(obj)
        try:
            return self._MODULE_REMAP[module]
        except KeyError:
            return module

    def is_defined_in_module(self, obj: object) -> bool:
        """Check if object is considered defined in the current module."""
        if self.module_name == "_nuke" \
                and inspect.getmodule(obj) is builtins \
                and obj.__name__ not in self._REAL_BUILTINS:
            return True

        return super().is_defined_in_module(obj)

    # def set_defined_names(self, defined_names: set[str]) -> None:
    #     super().set_defined_names(defined_names)
    #     for typ in ["Any", "Self", "Iterable", "Mapping"]:
    #         self.add_name(f"typing.{typ}", require=False)

    def strip_or_import(self, type_name: str) -> str:
        try:
            return super().strip_or_import(type_name.rstrip("."))
        except SyntaxError:
            print(f"Invalid type {type_name} in module {self.module_name}")
            return type_name


mypy.stubgen.InspectionStubGenerator = InspectionStubGenerator  # type: ignore[attr-defined,misc]
mypy.stubgenc.InspectionStubGenerator = InspectionStubGenerator  # type: ignore[misc]

mypy.moduleinspect.ModuleInspect = ModuleInspect
mypy.stubutil.ModuleInspect = ModuleInspect
mypy.stubgen.ModuleInspect = ModuleInspect


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Python stub generator for Nuke")
    parser.add_argument("outdir", help="The path to the output directory")
    args = parser.parse_args()

    outdir = Path(args.outdir)

    temp_out_dir = outdir / "stubgen_temp"

    modules = [
        "_nuke",
        "_curveknob",
        "_nuke_color",
        "_curvelib",
        "_geo",
        "_gsv",
        "_memory",
        "_localization",
        "_splinewarp",
    ]

    stubgen_args = [
        "--include-docstrings",
        "--output", str(temp_out_dir),
        "--package", "nuke_internal",
    ]
    for module in modules:
        stubgen_args.extend(("--module", module))

    mypy.stubgen.main(stubgen_args)

    # Now stitch the generated files together into the `nuke-stubs` package
    dest_dir = outdir / "nuke-stubs"

    nuke_internal_dir = temp_out_dir.joinpath("nuke_internal")
    for file in itertools.chain(temp_out_dir.iterdir(), nuke_internal_dir.iterdir()):
        if file.is_file() and file.suffix == '.pyi':
            if file.stem == "__init__":
                file.unlink()
            else:
                file.replace(dest_dir.joinpath(file.name))

    shutil.rmtree(temp_out_dir)
