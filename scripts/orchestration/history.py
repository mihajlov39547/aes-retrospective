"""Read-only historical indexing, never migration or automatic aggregation."""
from pathlib import Path
from .artifacts import read, hashes, check
from .configuration import safe_output
from .runner import write, identifier
from .platform import probe


def index_history(source, destination):
    source=Path(source).resolve(); destination=safe_output(destination)
    check(source.is_dir(),'Historical source does not exist')
    check(source!=destination and source not in destination.parents and destination not in source.parents,'History destination must not overlap source')
    current=probe(['git','rev-parse','HEAD']); records=[]
    for path in sorted(source.rglob('metadata.json')):
        if 'source' in path.relative_to(source).parts: continue
        meta=read(path)
        records.append(dict(relative_directory=path.parent.relative_to(source).as_posix(),experiment=meta.get('experiment'),seed=meta.get('seed'),purpose=meta.get('purpose'),
                            recorded_git_commit=meta.get('git_commit'),current_git_commit=current,commit_matches_current=meta.get('git_commit')==current if meta.get('git_commit') and current else None,
                            recorded_platform={k:meta.get(k) for k in ('os','machine','cpu','gpu','python','library_versions')},recorded_source_hashes=meta.get('source_sha256',meta.get('script_sha256')),artifact_hashes=hashes(path.parent),compatibility='Not assessed; not eligible for automatic pooling'))
    destination.mkdir(parents=True,exist_ok=True)
    target=destination/('history-'+identifier()+'.json')
    write(target,dict(schema_version=1,source=str(source),current_git_commit=current,records=records,notes='Read-only index. Missing metadata remains null. Includes hashes of unchanged native files; no validation or platform identity fabricated.'))
    return target
