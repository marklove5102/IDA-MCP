"""Custom monochrome sidebar icons drawn via QPainterPath."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, QSize
from PySide6.QtGui import (
    QColor,
    QIcon,
    QImage,
    QPainter,
    QPainterPath,
    QPixmap,
    QTransform,
)


def _icon_from_path(path: QPainterPath, color: QColor, size: int = 22) -> QIcon:
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawPath(path)
    painter.end()
    return QIcon(QPixmap.fromImage(image))


def _chat_path() -> QPainterPath:
    bubble = QPainterPath()
    bubble.addRoundedRect(QRectF(3.0, 3.0, 16.0, 11.0), 3.0, 3.0)
    tail = QPainterPath()
    tail.moveTo(7.0, 14.0)
    tail.lineTo(5.5, 18.5)
    tail.lineTo(11.0, 14.0)
    tail.closeSubpath()
    return bubble.united(tail)


def _folder_path() -> QPainterPath:
    body = QPainterPath()
    body.addRoundedRect(QRectF(2.0, 7.0, 18.0, 11.0), 2.0, 2.0)
    tab = QPainterPath()
    tab.moveTo(2.0, 7.0)
    tab.lineTo(2.0, 5.5)
    tab.quadTo(2.0, 4.0, 3.5, 4.0)
    tab.lineTo(8.5, 4.0)
    tab.quadTo(9.5, 4.0, 10.0, 5.0)
    tab.lineTo(10.5, 6.0)
    tab.lineTo(10.5, 7.0)
    return body.united(tab)


def _gear_path() -> QPainterPath:
    center = QPointF(11.0, 11.0)
    gear = QPainterPath()
    gear.addEllipse(QRectF(5.5, 5.5, 11.0, 11.0))
    tooth = QPainterPath()
    tooth.addRoundedRect(QRectF(9.5, 1.5, 3.0, 4.5), 1.0, 1.0)
    for angle in range(0, 360, 45):
        t = QTransform()
        t.translate(center.x(), center.y())
        t.rotate(angle)
        t.translate(-center.x(), -center.y())
        gear = gear.united(t.map(tooth))
    hole = QPainterPath()
    hole.addEllipse(QRectF(8.2, 8.2, 5.6, 5.6))
    return gear.subtracted(hole)


def _status_path() -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(QRectF(3.0, 13.5, 3.5, 5.5), 1.0, 1.0)
    path.addRoundedRect(QRectF(9.0, 8.5, 3.5, 10.5), 1.0, 1.0)
    path.addRoundedRect(QRectF(15.0, 4.0, 3.5, 15.0), 1.0, 1.0)
    base = QPainterPath()
    base.addRoundedRect(QRectF(2.0, 19.0, 18.0, 1.5), 0.5, 0.5)
    return path.united(base)


_SIDEBAR_ICON_FACTORIES = {
    "chat": _chat_path,
    "fs": _folder_path,
    "settings": _gear_path,
    "status": _status_path,
}


def make_sidebar_icons(
    color: str | QColor = "", size: int = 22
) -> dict[str, QIcon]:
    """Create all sidebar icons in the given color.

    If *color* is empty, falls back to the theme sidebar icon color.
    """
    if not color:
        from app.ui.theme import Theme
        color = Theme.light().sidebar_icon_color
    qcolor = QColor(color)
    return {
        key: _icon_from_path(factory(), qcolor, size)
        for key, factory in _SIDEBAR_ICON_FACTORIES.items()
    }
