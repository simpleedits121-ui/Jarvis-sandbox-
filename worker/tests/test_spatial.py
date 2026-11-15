from pathlib import Path
import pytest
from jarvis_worker.spatial import SpatialEngine

def test_create_and_transform_scene(tmp_path):
    engine=SpatialEngine(tmp_path)
    obj=engine.operation({"operation":"create_primitive","type":"sphere","name":"Head",
        "parameters":{"radius":[1,2,1]},"transform":{"position":[0,1,0]}})
    assert obj["name"]=="Head"
    updated=engine.operation({"operation":"transform","object_id":obj["id"],
        "transform":{"position":[1,2,3]}})
    assert updated["transform"]["position"]==[1,2,3]

def test_reject_unknown_primitive(tmp_path):
    engine=SpatialEngine(tmp_path)
    with pytest.raises(ValueError):
        engine.operation({"operation":"create_primitive","type":"arbitrary_code"})

def test_nano_build_records_workers_and_components(tmp_path):
    engine=SpatialEngine(tmp_path)
    result=engine.build_demo("Build a humanoid blockout")
    assert result["created"]==9
    snap=engine.snapshot()
    assert len(snap["scene"]["objects"])==9
    assert {e["worker"] for e in snap["recent_events"]} >= {"surveyor","structural_builder","skin_workers","detail_workers","inspector"}

def test_scene_persists(tmp_path):
    engine=SpatialEngine(tmp_path)
    engine.build_demo("Build")
    reopened=SpatialEngine(tmp_path)
    assert len(reopened.snapshot()["scene"]["objects"])==9
