import argparse
import builtins
import inspect
import itertools
import re
import shutil
from pathlib import Path

import mypy.stubgen
import mypy.stubgenc
from mypy.stubgenc import DocstringSignatureGenerator, SignatureGenerator

import nuke
import stubgenlib.moduleinspect
from stubgenlib.siggen import (
    AdvancedSigMatcher,
    AdvancedSignatureGenerator,
)


_fuzzy_bool = re.compile("bool(?:ean)?", re.IGNORECASE)
_fuzzy_float = re.compile("float?", re.IGNORECASE)
_fuzzy_int = re.compile("int(?:eger)?", re.IGNORECASE)
_fuzzy_string = re.compile("str(?:ing)?", re.IGNORECASE)
_fuzzy_string_list = re.compile(r"str(?:ing)?\s+list\.?", re.IGNORECASE)


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
        result_type_overrides={
            ("_nuke.AnimationCurve.keys", "*"): "list[AnimationKey]",
            ("_nuke.AnimationCurve.setKey", "*"): "AnimationKey",
            ("_nuke.Array_Knob.animation", "*"): "AnimationCurve | None",
            ("_nuke.Array_Knob.animations", "*"): "list[AnimationCurve]",
            ("_nuke.Array_Knob.deleteAnimation", "*"): "None",
            ("_nuke.Knob.ClassID", "*"): "int",
            ("_nuke.Knob.label", "*"): "str",
            ("_nuke.Knob.name", "*"): "str",
            ("_nuke.Knob.tooltip", "*"): "str",
            ("_nuke.Node.input", "*"): "Node | None",
            ("_nuke.Node.inputs", "*"): "int",
            ("_nuke.Node.isCloneable", "*"): "bool",
            ("_nuke.Node.numKnobs", "*"): "int",
            ("_nuke.Node.parent", "*"): "Group",
            ("_nuke.Node.performanceInfo", "*"): "dict[str, Any]",
            ("_nuke.Node.shown", "*"): "bool",
            ("_nuke.GeoSelect_Knob.*", "listoflistsoffloats"): "list[list[float]]",
            ("_nuke.Group.*", "NodeorNone."): "Node | None",
            ("_nuke.addFormat", "*"): "Format | None",
            ("_nuke.*.Class", "*"): "str",
            ("_nuke.*.writeKnobs", "*"): "str",
            ("_nuke.*", "knob"): "Knob",
            ("_nuke.*", "MenuorNone"): "Menu | None",
            ("_nuke.*", "Trueif*"): "bool",
            ("_nuke.*", "nuke.Node"): "Node",
            ("_nuke.*", "Listofnodes"): "list[Node]",
            ("_nuke.*", "Listofnodes."): "list[Node]",
            ("_nuke.*", "Listofstrings."): "list[str]",
            ("_nuke.*", "floatlist."): "list[float]",
            ("_nuke.*", "*[Nn]umberof*"): "int",
            ("_nuke.*", "Thesubmenuthatwasadded."): "Menu",
            ("_nuke.*", "Theseparatorthatwascreated."): "MenuItem",
            # NOTE: Keep these blanket patterns at the end so they don't interfere with any of
            # the more targeted remapping patterns.
            ("_nuke.*", _fuzzy_string_list): "list[str]",
            ("*", _fuzzy_bool): "bool",
            ("*", _fuzzy_float): "float",
            ("*", _fuzzy_int): "int",
            ("*", _fuzzy_string): "str",
        },
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


stubgenlib.moduleinspect.patch()

mypy.stubgen.InspectionStubGenerator = InspectionStubGenerator  # type: ignore[attr-defined,misc]
mypy.stubgenc.InspectionStubGenerator = InspectionStubGenerator  # type: ignore[misc]


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
