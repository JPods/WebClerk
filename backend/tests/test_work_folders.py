"""Work folders (Bill, 2026-09-27): one manifest owns WORK_DIR; nothing builds a path by hand."""
import os
import time

import pytest

from common import work_folders as wf


@pytest.fixture
def work(settings, tmp_path):
    settings.WORK_DIR = str(tmp_path / 'work')
    return tmp_path / 'work'


def test_a_named_folder_is_made_owner_only_and_the_manifest_is_seeded(work):
    path = wf.work_folder('bundles', 'journal')
    assert path == work / 'bundles' / 'journal' and path.is_dir()
    assert (work / 'manifest.json').exists()
    assert oct(os.stat(work).st_mode & 0o777) == '0o700'


def test_an_unknown_folder_or_a_climbing_part_is_refused(work):
    with pytest.raises(KeyError):
        wf.work_folder('anything')
    for bad in ('..', 'a/b', '.hidden', ''):
        with pytest.raises(ValueError):
            wf.work_folder('bundles', bad)


def test_the_company_manifest_keeps_its_rules_and_gains_new_folders(work):
    import json
    wf.manifest()
    mine = json.loads((work / 'manifest.json').read_text())
    mine['folders']['logs']['keep_days'] = 3
    del mine['folders']['ship']
    (work / 'manifest.json').write_text(json.dumps(mine))
    folders = wf.manifest()
    assert folders['logs']['keep_days'] == 3 and 'ship' in folders


def test_scrub_prunes_past_keep_days_keeps_the_digest_and_names_strays(work):
    old = time.time() - 40 * 86400
    stale = wf.work_folder('logs') / 'old.log'
    stale.write_text('x'); os.utime(stale, (old, old))
    fresh = wf.work_folder('logs') / 'new.log'
    fresh.write_text('x')
    digest = wf.work_folder('imports/digest') / '2026-01-01.jsonl'
    digest.write_text('{}'); os.utime(digest, (old, old))
    (work / 'mystery').mkdir()
    dry = wf.scrub(dry_run=True)
    assert dry['pruned'] == {'logs': 1} and stale.exists()
    result = wf.scrub()
    assert not stale.exists() and fresh.exists() and digest.exists()
    assert result['strays'] == ['mystery'] and result['backup']['offsite_waiting'] == ['imports/digest']


@pytest.mark.django_db
def test_a_document_is_found_by_its_key_wherever_the_data_folder_is(settings, tmp_path):
    from apps.docs.models import Document
    from apps.docs.views.upload_view import document_file
    settings.DATA_DIR = str(tmp_path / 'moved-data')
    doc = Document(path={'storage': 'local', 'key': 'uploads/document/2026/09/a.pdf',
                         'full': '/old/machine/data/uploads/document/2026/09/a.pdf'})
    assert document_file(doc) == os.path.realpath(str(tmp_path / 'moved-data' / 'uploads/document/2026/09/a.pdf'))
    doc.path = {'key': '../../etc/passwd'}
    assert document_file(doc) is None


def test_backups_copy_by_rule_never_delete_and_keep_certs_home(work, settings, tmp_path):
    import json
    settings.DATA_DIR = str(tmp_path / 'data')
    wf.manifest()
    mine = json.loads((work / 'manifest.json').read_text())
    mine['backup_targets']['offsite'] = str(tmp_path / 'away')
    mine['folders']['certs']['backup'] = 'offsite'            # even if someone asks, certs stay home
    (work / 'manifest.json').write_text(json.dumps(mine))
    (wf.work_folder('imports/digest') / 'd.jsonl').write_text('{}')
    (wf.work_folder('certs') / 'c.pem').write_text('secret')
    (wf.work_folder('logs') / 'l.log').write_text('x')          # backup: none
    first = wf.back_up()
    assert first['copied']['imports/digest'] == {'local': 1, 'offsite': 1}
    assert (tmp_path / 'data/work-backup/imports/digest/d.jsonl').exists()
    assert (tmp_path / 'away/imports/digest/d.jsonl').exists()
    assert not (tmp_path / 'away/certs').exists() and (tmp_path / 'data/work-backup/certs/c.pem').exists()
    assert 'logs' not in first['copied']
    (wf.work_folder('imports/digest') / 'd.jsonl').unlink()
    again = wf.back_up()
    assert again['copied']['imports/digest'] == {'local': 0, 'offsite': 0}
    assert (tmp_path / 'away/imports/digest/d.jsonl').exists(), 'a backup never deletes'


def test_scrub_copies_before_it_prunes(work, settings, tmp_path):
    settings.DATA_DIR = str(tmp_path / 'data')
    old = time.time() - 400 * 86400
    f = wf.work_folder('audits') / 'old.json'                  # audits: keep 365, backup local
    f.write_text('{}'); os.utime(f, (old, old))
    wf.scrub()
    assert not f.exists() and (tmp_path / 'data/work-backup/audits/old.json').exists()
