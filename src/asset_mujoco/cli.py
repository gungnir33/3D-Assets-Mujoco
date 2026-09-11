"""python -m asset_mujoco.cli；stdout 为 JSON，错误码区分验证层。"""
import argparse
import json
from pathlib import Path
import sys
from pydantic import ValidationError
from .contracts import ConversionRequest,ValidationResult
from .inputs import inspect_input
from .manifest import save_review,checked_report

def main(argv=None):
    parser=argparse.ArgumentParser()
    commands=parser.add_subparsers(dest="command",required=True)
    inspect=commands.add_parser("inspect")
    inspect.add_argument("input",type=Path)
    report=commands.add_parser("report")
    report.add_argument("package",type=Path)
    review=commands.add_parser("review")
    review.add_argument("package",type=Path)
    review.add_argument("--reviewer",required=True)
    review.add_argument("--decision",required=True,choices=["approved","rejected"])
    review.add_argument("--images",nargs="+",required=True)
    convert=commands.add_parser("convert")
    convert.add_argument("input",type=Path)
    convert.add_argument("--output",required=True,type=Path)
    convert.add_argument("--name",default="asset")
    convert.add_argument("--source-up",choices=["x","y","z"])
    convert.add_argument("--scale",type=float)
    convert.add_argument("--target-size-m",type=float,nargs=3)
    convert.add_argument("--yaw-deg",type=float,default=0)
    convert.add_argument("--scale-mode",choices=["uniform","fit_axes"],default="uniform")
    convert.add_argument("--body-mode",choices=["static","free"],default="static")
    convert.add_argument("--mass",type=float)
    convert.add_argument("--inertia-mode",choices=["box_approx","supplied"])
    convert.add_argument("--supplied-inertia",type=Path)
    convert.add_argument("--collision-mode",choices=["hull","none"],default="hull")
    convert.add_argument("--validation-level",choices=["compile","physics","full"],default="full")
    args=vars(parser.parse_args(argv))
    command=args.pop("command")
    try:
        if command=="inspect":
            path,raw=inspect_input(args["input"])
            print(json.dumps({"file":str(path),"raw":raw}))
            return 0
        if command=="report":
            package=args["package"]
            result=checked_report(package)
            print(json.dumps({"status":result.aggregate(),**result.model_dump()}))
            return 0
        if command=="review":
            print(json.dumps(save_review(args["package"],args["reviewer"],args["decision"],args["images"])))
            return 0
        if args["supplied_inertia"]:
            args["supplied_inertia"]=json.loads(args["supplied_inertia"].read_text())
        request=ConversionRequest(**args)
        from .pipeline import convert as run
        package=run(request)
        result=ValidationResult.model_validate_json((package/"validation_report.json").read_text())
        print(json.dumps({"package":str(package),"status":result.aggregate(),**result.model_dump()}))
        return 0
    except (ValidationError,FileNotFoundError) as error:
        print(json.dumps({"error":{"code":"INVALID_INPUT","message":str(error)}}))
        return 2
    except Exception as error:
        message=str(error)
        code=7 if "RENDER_UNAVAILABLE" in message else 5 if any(x in message for x in ("RENDER_FAILED","ASSET_CONTACT","NONFINITE","SIMULATION_WARNING","TIME_RESET")) else 4 if "Element" in message or "XML" in message else 3
        print(json.dumps({"error":{"code":"CONVERSION_FAILED","message":message}}))
        return code

if __name__=="__main__":
    sys.exit(main())
