import pytest
from annotate import _center, _midpoint


@pytest.mark.parametrize(
    argnames=("pt1", "pt2", "expected_midpoint"),
    argvalues=[
        ((0, 0), (10, 10), (5, 5)),
        ((1, 3), (5, 7), (3, 5)),
        ((2, 4), (6, 8), (4, 6)),
    ],
)
def test_midpoint(pt1, pt2, expected_midpoint):
    """
    Given two points on a Cartesian plane, test whether
    `annotate._midpoint` produces the correct midpoint between
    those two points.
    """
    assert _midpoint(pt1, pt2) == expected_midpoint


@pytest.mark.parametrize(
    argnames=("box", "expected_center_point"),
    argvalues=[
        ((0, 0, 10, 10), (5, 5)),
        ((1, 3, 5, 7), (3, 5)),
        ((2, 4, 6, 8), (4, 6)),
    ],
)
def test_center(box, expected_center_point):
    """
    Given a box (x1, y1, x2, y2) with (x1, y1) representing
    the top-left corner and (x2, y2) the bottom-right corner
    of the box respectively, test whether `annotate._center`
    produces the correct center point (c1, c2) of the box.
    """
    assert _center(box) == expected_center_point
