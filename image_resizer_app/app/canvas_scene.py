from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

class CanvasScene(QGraphicsView):
    def __init__(self, parent=None, on_error=None):
        super().__init__(parent)

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.image_item = None
        self.pixmap = None
        self.on_error = on_error

    def load_image(self, pixmap: QPixmap):
        self.scene.clear()
        self.pixmap = pixmap

        self.image_item = self.scene.addPixmap(pixmap)
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.setSceneRect(pixmap.rect().toRectF())
