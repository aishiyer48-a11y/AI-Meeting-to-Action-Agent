import database.db as db
from database import crud


def test_crud(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    task_id = crud.create_task("Write docs", "Rahul", "Friday", "High", "meeting")
    assert crud.get_task(task_id)["task"] == "Write docs"
    assert crud.update_task(task_id, status="Done")
    assert crud.get_task(task_id)["status"] == "Done"
    assert crud.get_all_tasks()
    assert crud.delete_task(task_id)
    assert crud.get_task(task_id) is None
