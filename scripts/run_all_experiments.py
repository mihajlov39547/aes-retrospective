"""Cross-platform sequential experiment orchestrator (JSON configuration)."""
import argparse
import json
import sys
from pathlib import Path
from orchestration.configuration import ROOT, load
from orchestration.registry import REGISTRY, command
from orchestration.platform import detect
from orchestration.runner import create, execute, tasks, verify_suite, preflight
from orchestration.aggregation import aggregate


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='action',required=True)
    sub.add_parser('list')
    doctor=sub.add_parser('doctor'); doctor.add_argument('--config',type=Path)
    history=sub.add_parser('import-history'); history.add_argument('--source',required=True,type=Path); history.add_argument('--destination',required=True,type=Path)
    for action in ('plan','run'):
        c=sub.add_parser(action); c.add_argument('--config',required=True,type=Path)
        c.add_argument('--platform-alias'); c.add_argument('--select',nargs='+',choices=[k for k,v in REGISTRY.items() if v['status']=='active'])
    for action in ('resume','verify','aggregate'):
        c=sub.add_parser(action); c.add_argument('--run-dir',required=True,type=Path)
        if action=='resume':
            c.add_argument('--retry-failed',action='store_true'); c.add_argument('--retry-skipped',action='store_true')
    args=p.parse_args(argv)
    try:
        if args.action=='list': print(json.dumps(REGISTRY,indent=2)); return 0
        if args.action=='import-history':
            from orchestration.history import index_history
            print(index_history(args.source,args.destination)); return 0
        if args.action=='doctor':
            config=load(args.config) if args.config else None
            env=detect(config)
            if config: env['preflight']={n:preflight(n,o,config,env,config['output_root']) for n,_,o in tasks(config)}
            print(json.dumps(env,indent=2)); return 0
        if args.action in ('plan','run'):
            config=load(args.config)
            if args.platform_alias:
                import re
                if not re.fullmatch('[A-Za-z0-9_-]+',args.platform_alias): raise ValueError('Invalid platform alias')
                config['platform_alias']=args.platform_alias
            if args.select:
                if set(args.select)-set(config['experiments']): raise ValueError('Selection includes experiments not enabled in config')
                config['experiments']={n:v for n,v in config['experiments'].items() if n in args.select}
            if args.action=='plan':
                print(json.dumps(dict(config=config,ordering=[dict(experiment=n,seed=s,command=command(n,o,s,config['execution_profile'],Path('<ATTEMPT_STAGING>'),ROOT)) for n,s,o in tasks(config)],note='No CUDA initialization, buffers, measurements or output directories. Run performs live preflight.'),indent=2)); return 0
            env=detect(config); directory=create(config,env)
            print('Run directory: '+str(directory),flush=True)
            return 0 if execute(directory) else 1
        if args.action=='resume': return 0 if execute(args.run_dir,args.retry_failed,args.retry_skipped) else 1
        if args.action=='verify':
            result=verify_suite(args.run_dir); print(json.dumps(result,indent=2)); return 0 if result['passed'] else 1
        if args.action=='aggregate': print(aggregate(args.run_dir)); return 0
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print('Orchestration error: '+str(exc),file=sys.stderr); return 1
    except KeyboardInterrupt:
        print('Interrupted; resume the recorded run directory.',file=sys.stderr); return 130


if __name__=='__main__': sys.exit(main())
