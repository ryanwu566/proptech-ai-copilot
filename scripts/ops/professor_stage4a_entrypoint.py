#!/usr/bin/env python3
"""Stage 4A startup profile, separate from the accepted Stage 2 entrypoint."""
from __future__ import annotations
import json
import os
from pathlib import Path
import resource
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from services.selfhost_secret_files import CORE, SecretRefused, read_secret, runtime_environment, install_log_redaction
from services.professor_userdb import DATABASE_ENV, validate_url


def environment(core, user_directory, inherited, *, owner=0,gid=10001):
    if (DATABASE_ENV in inherited or DATABASE_ENV+'_FILE' in inherited
        or inherited.get('PROFESSOR_USERDB_ENABLED')!='true'):
        raise SecretRefused('userdb_profile_invalid')
    result=runtime_environment(core,inherited,owner=owner,gid=gid)
    if set(os.listdir(user_directory))!={'professor_user_database_url'}:
        raise SecretRefused('userdb_mount_invalid')
    try:
        result[DATABASE_ENV]=validate_url(read_secret(user_directory,'professor_user_database_url',owner=owner,gid=gid))
    except ValueError:
        raise SecretRefused('user_database_url_invalid') from None
    return result


def main():
    try:
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        mode=sys.argv[1:] or ['api']
        if mode not in [['api'],['validate'],['health']]:
            raise SecretRefused('invalid_arguments')
        result=environment(Path('/run/secrets'),Path('/run/professor-userdb'),dict(os.environ))
        install_log_redaction([result[n] for n in (*CORE.values(),DATABASE_ENV)])
        os.environ.clear(); os.environ.update(result)
        from services.professor_userdb import validate_configuration
        validate_configuration()
        if mode==['validate']:
            print(json.dumps({'status':'PASS','profile':'stage4a-hybrid','values_returned':False})); return 0
        if mode==['health']:
            from scripts.ops.selfhost_runtime import health
            print(json.dumps(health(Path('/run/secrets')))); return 0
        import uvicorn
        # Disable access URLs: credentials must never be accepted/logged in query strings.
        uvicorn.run('backend.api_main:app',host='0.0.0.0',port=8080,proxy_headers=False,access_log=False)
        return 0
    except Exception:
        print(json.dumps({'status':'REFUSED','reason_code':'stage4a_configuration_unavailable','values_returned':False})); return 1


if __name__=='__main__': raise SystemExit(main())
