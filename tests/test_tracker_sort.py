import pytest


def test_sort_tracker_import_and_update():
    try:
        from tracker_sort import SortTracker
    except Exception as e:
        pytest.skip("SortTracker dependencies not installed: %s" % e)

    t = SortTracker()
    # two simple detections
    dets = [{"bbox": [10, 10, 50, 50]}, {"bbox": [100, 100, 140, 140]}]
    tracks = t.update(dets)
    assert len(tracks) >= 2
    # Update with moved detections; should maintain ids
    dets2 = [{"bbox": [12, 12, 52, 52]}, {"bbox": [102, 102, 142, 142]}]
    tracks2 = t.update(dets2)
    ids1 = {tr['id'] for tr in tracks}
    ids2 = {tr['id'] for tr in tracks2}
    assert ids1 <= ids2 or ids2 <= ids1
