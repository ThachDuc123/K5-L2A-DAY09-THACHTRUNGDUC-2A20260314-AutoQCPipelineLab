from pipeline.checks import aspect_ratio


def test_flags_extreme_tall_and_wide_boxes(make_ds, cfg):
    cfg["aspect_ratio"] = {"max_ratio": 7.0}
    ds = make_ds(
        images={"a": 1},
        labels={
            "a": [
                "1 0.5 0.5 0.2 0.2",     # 1.0 -> ổn
                "1 0.5 0.5 0.02 0.3",    # (12.8 x 144.0) -> 11.25 > 7
                "0 0.5 0.5 0.5 0.05",    # (320.0 x 24.0) -> 13.33 > 7
            ]
        },
        size=(640, 480),
    )
    iss = aspect_ratio.run(ds, cfg)
    assert [(i.check, i.severity, i.code, i.image, i.line) for i in iss] == [
        ("aspect_ratio", "warn", "BOX_ASPECT_RATIO", "a", 2),
        ("aspect_ratio", "warn", "BOX_ASPECT_RATIO", "a", 3),
    ]
    assert iss[0].extra["class"] == "person"
    assert abs(iss[0].extra["ratio"] - 11.25) < 0.05
    assert abs(iss[1].extra["ratio"] - 13.33) < 0.05


def test_reads_threshold_from_cfg_and_boundary(make_ds, cfg):
    ds = make_ds(
        images={"a": 1},
        labels={"a": ["0 0.5 0.5 0.5 0.1"]},   # (250 x 50) -> đúng 5.0
        size=(500, 500),
    )
    cfg["aspect_ratio"] = {"max_ratio": 5.0}
    assert aspect_ratio.run(ds, cfg) == []     # đúng bằng ngưỡng không báo

    cfg["aspect_ratio"] = {"max_ratio": 4.9}
    iss = aspect_ratio.run(ds, cfg)
    assert [(i.line, i.extra["ratio"]) for i in iss] == [(1, 5.0)]


def test_uses_pixel_dimensions_not_normalized(make_ds, cfg):
    cfg["aspect_ratio"] = {"max_ratio": 4.0}
    ds = make_ds(
        images={"wide": 1},
        labels={
            "wide": [
                "1 0.5 0.5 0.05 0.25",   # 50 x 50 px -> 1.0 (chỉ lệch trên hệ chuẩn hoá)
                "0 0.5 0.5 0.2 0.2",     # 200 x 40 px -> 5.0 (hình vuông chuẩn hoá nhưng dẹt theo pixel)
            ]
        },
        size=(1000, 200),
    )
    iss = aspect_ratio.run(ds, cfg)
    assert [(i.line, i.extra["w_px"], i.extra["h_px"]) for i in iss] == [(2, 200.0, 40.0)]


def test_ignores_corrupt_lines_missing_labels_and_bad_images(make_ds, cfg):
    ds = make_ds(
        images={"bad": b"not-an-image", "nolbl": 2, "messy": 3},
        labels={
            "messy": [
                "bad line",
                "",
                "1 nan 0.5 0.1 0.1",
                "1 0.5 0.5 0 0.3",
                "93 0.5 0.5 0.01 0.4",   # id lạ nhưng vẫn đủ 5 cột hợp lệ -> vẫn đo tỉ lệ
            ]
        },
        size=(400, 400),
    )
    iss = aspect_ratio.run(ds, {"aspect_ratio": {"max_ratio": 7.0}})
    assert [(i.image, i.line, i.extra["class"]) for i in iss] == [("messy", 5, "93")]
