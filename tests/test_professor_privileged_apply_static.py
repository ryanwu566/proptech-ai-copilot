"""Inspect the privileged program without executing any apply behavior."""
import ast
from pathlib import Path

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/ops/professor_server_privileged_apply.sh'


def parsed_program():
    source=SCRIPT.read_text()
    body=source.split("<<'PY'\n",1)[1].rsplit('\nPY\n',1)[0]
    return source,ast.parse(body)


def reconciliation_call(tree):
    return next(node for node in ast.walk(tree)
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='run'
        and node.args and isinstance(node.args[0],ast.List)
        and any(isinstance(value,ast.Constant) and value.value=='scripts/ops/reconcile_plvr_special_notes.py'
                for value in node.args[0].elts)
        and any(isinstance(value,ast.Constant) and value.value=='--serving-export' for value in node.args[0].elts))


def test_readonly_reconciler_has_private_disk_temporary_workspace():
    source,tree=parsed_program()
    call=reconciliation_call(tree)
    constants=[item.value for item in call.args[0].elts if isinstance(item,ast.Constant)]
    assert '--read-only' in constants
    assert 'SQLITE_TMPDIR=/evidence/sqlite-temp' in constants
    assert 'TMPDIR=/evidence/sqlite-temp' in constants
    assert "scratch=OUT/'sqlite-temp'" in source
    assert 'scratch.mkdir(mode=0o700)' in source
    assert source.index('scratch.mkdir(mode=0o700)')<source.index('reconciliation=run(')


def test_reconciler_failure_json_is_preserved_before_exit_gate():
    source,tree=parsed_program()
    call=reconciliation_call(tree)
    assert any(keyword.arg=='check' and isinstance(keyword.value,ast.Constant) and keyword.value.value is False
               for keyword in call.keywords)
    assert "save('reconciliation-result.json'," in source
    assert source.index("save('reconciliation-result.json',")<source.index('require(reconciliation.returncode==0,')


def test_all_embedded_python_programs_parse_without_execution():
    _,tree=parsed_program()
    def value(node):
        if isinstance(node,ast.Constant): return node.value
        if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Add): return value(node.left)+value(node.right)
        raise AssertionError('embedded program is not literal source')
    found=set()
    for node in tree.body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id in {'ENTRYPOINT','SECURITY','VERIFY_ARTIFACTS'}:
                    ast.parse(value(node.value));found.add(target.id)
    assert found=={'ENTRYPOINT','SECURITY','VERIFY_ARTIFACTS'}


def test_image_code_directories_remain_traversable_under_private_umask(tmp_path):
    """Application code permissions must also permit cap-dropped UID0 jobs."""
    import os,shutil,stat
    _,tree=parsed_program()
    function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='stage_image_context')
    # Execute only this pure staging component on a disposable fixture; never
    # execute the privileged orchestrator or any Docker/database action.
    module=ast.Module(body=[function],type_ignores=[])
    namespace={'shutil':shutil}
    exec(compile(module,'<stage-image-context-test>','exec'),namespace)
    repo=tmp_path/'repo';repo.mkdir()
    script=repo/'scripts/ops/reconcile_plvr_special_notes.py'
    script.parent.mkdir(parents=True);script.write_text('print("fixture")\n')
    context=tmp_path/'private-context';context.mkdir(mode=0o700)
    old_umask=os.umask(0o077)
    try:
        namespace['stage_image_context'](repo,context,['scripts/ops/reconcile_plvr_special_notes.py'],'# fixture entrypoint\n')
    finally:
        os.umask(old_umask)
    app=context/'app'
    for directory in [app,*(p for p in app.rglob('*') if p.is_dir())]:
        assert stat.S_IMODE(directory.stat().st_mode)==0o755
    assert stat.S_IMODE(context.stat().st_mode)==0o700
    assert stat.S_IMODE((app/'scripts/ops/reconcile_plvr_special_notes.py').stat().st_mode)==0o644
    assert script.read_text()=='print("fixture")\n'


def test_same_identity_launch_preflight_precedes_real_reconciliation():
    source,tree=parsed_program()
    call=next(node for node in ast.walk(tree)
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='run'
        and node.args and isinstance(node.args[0],ast.List)
        and any(isinstance(value,ast.Constant) and value.value=='--help' for value in node.args[0].elts))
    constants=[n.value for n in call.args[0].elts if isinstance(n,ast.Constant)]
    assert '--read-only' in constants and '--cap-drop' in constants and 'ALL' in constants
    assert '--user' in constants and '0:0' in constants
    assert 'scripts/ops/reconcile_plvr_special_notes.py' in constants
    assert source.index("require(launch.returncode==0,")<source.index('reconciliation=run(')
