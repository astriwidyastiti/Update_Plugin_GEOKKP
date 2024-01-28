import math

from qgis.PyQt import QtGui, QtCore

from qgis.core import (
    QgsCircle,
    QgsPoint,
    QgsPointXY,
    QgsFeature,
    QgsGeometry,
    QgsCircularString,
    QgsSnappingConfig,
    QgsProject,
    QgsTolerance,
)

from qgis.PyQt.QtCore import pyqtSignal
from qgis.gui import QgsMapTool, QgsVertexMarker, QgsRubberBand, QgsGeometryRubberBand


# ----------------------------------------------------------- #
#                      Point Dimension                        #
# ----------------------------------------------------------- #
class DimensionPointTool(QgsMapTool):

    completed = pyqtSignal()

    def __init__(self, canvas, dimension_layer):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas

        enable_snapping()

        self.dimension_layer = dimension_layer

        self.vm = create_vertex_marker(self.canvas, "BOX")

    def canvasMoveEvent(self, event):
        point_snap, status = snapping_point(self.canvas, event.pos())
        self.vm.setCenter(point_snap)

    def canvasReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            pt, _ = snapping_point(self.canvas, event.pos())

            geom_line_zero_length = QgsGeometry().fromPolylineXY([pt, pt])

            feat = QgsFeature()
            feat.setGeometry(geom_line_zero_length)
            titik_nilai = str(round(pt.x(), 3)) + "," + str(round(pt.y(), 3))
            feat.setAttributes(["Titik", titik_nilai])

            self.dimension_layer_prov = self.dimension_layer.dataProvider()
            self.dimension_layer.startEditing()
            self.dimension_layer_prov.addFeatures([feat])
            self.dimension_layer.commitChanges()
        elif event.button() == QtCore.Qt.RightButton:
            try:
                self.canvas.scene().removeItem(self.vm)
            except NameError:
                pass

            self.completed.emit()


# ----------------------------------------------------------- #
#                      Angle Dimension                        #
# ----------------------------------------------------------- #
class DimensionAngleTool(QgsMapTool):

    completed = pyqtSignal()

    def __init__(self, canvas, dimension_layer):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas

        enable_snapping()

        self.dimension_layer = dimension_layer

        self.vm_center = create_vertex_marker(self.canvas, "CIRCLE")
        self.vm_1 = create_vertex_marker(self.canvas, "CROSS")
        # self.vm_1.hide()
        self.vm_2 = create_vertex_marker(self.canvas, "CROSS")
        # self.vm_2.hide()

        self.rb_buffer = create_rubberband(self.canvas, "SOLID")
        self.geomrb_buffer = create_geom_rubberband(self.canvas, "SOLID")
        # self.geomrb_buffer.hide()
        self.geomrb_short_arc = create_geom_rubberband(self.canvas, "DOT_LINE")
        # self.geomrb_short_arc.hide()
        self.geomrb_long_arc = create_geom_rubberband(self.canvas, "DOT_LINE")
        # self.geomrb_long_arc.hide()

        self.click_counter = 0

    def canvasMoveEvent(self, event):
        point_snap, status = snapping_point(self.canvas, event.pos())
        if self.click_counter == 0:  # add center point
            # self.vm_center.show()
            self.vm_center.setCenter(point_snap)

        elif self.click_counter == 1:  # create estimate buffer
            # self.geomrb_buffer.show()
            cur_pt = QgsPoint(point_snap)
            circle = QgsCircle.fromCenterPoint(self.center_pt, cur_pt)
            self.circular_string = circle.toCircularString()
            self.geomrb_buffer.setGeometry(self.circular_string)

        elif self.click_counter == 2:  # get first arc point
            cur_pt = QgsPoint(point_snap)
            _, start_arc, _, _ = self.circular_string.closestSegment(cur_pt)
            # self.vm_1.show()
            self.vm_1.setCenter(QgsPointXY(start_arc))

        elif self.click_counter == 3:  # get second arc point
            cur_pt = QgsPoint(point_snap)
            _, end_arc, _, _ = self.circular_string.closestSegment(cur_pt)
            # self.vm_2.show()
            self.vm_2.setCenter(QgsPointXY(end_arc))

        elif self.click_counter == 4:  # choose segment
            p = QgsPoint(point_snap)

            arc = self.check_arc(p, self.shortest_arc, self.longest_arc)
            self.canvas.refresh()
            self.final_arc = arc

    def canvasReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.click_counter += 1
            point_snap, _ = snapping_point(self.canvas, event.pos())
            cur_pt = QgsPoint(point_snap)

            if self.click_counter == 1:  # center point stored
                self.center_pt = QgsPoint(point_snap)
                self.vm_center.setCenter(point_snap)

            elif self.click_counter == 2:  # radius point stored
                self.radius_pt = QgsPointXY(point_snap)

            elif self.click_counter == 3:  # start arc stored
                _, start_arc, _, _ = self.circular_string.closestSegment(cur_pt)
                self.start_arc_pt = start_arc

            elif self.click_counter == 4:  # end arc stored
                _, end_arc, _, _ = self.circular_string.closestSegment(cur_pt)
                self.end_arc_pt = end_arc

                self.shortest_arc = QgsCircularString().fromTwoPointsAndCenter(
                    self.start_arc_pt, self.end_arc_pt, self.center_pt, True
                )
                self.longest_arc = QgsCircularString().fromTwoPointsAndCenter(
                    self.start_arc_pt, self.end_arc_pt, self.center_pt, False
                )
                # self.geomrb_buffer.hide()
                self.geomrb_short_arc.setGeometry(self.shortest_arc)
                # self.geomrb_short_arc.show()
                self.geomrb_long_arc.setGeometry(self.longest_arc)
                # self.geomrb_long_arc.show()

            elif self.click_counter == 5:  # arc finalised
                start_az = self.center_pt.azimuth(self.start_arc_pt)
                end_az = self.center_pt.azimuth(self.end_arc_pt)
                if start_az < 0:
                    start_az = 360 + start_az
                if end_az < 0:
                    end_az = 360 + end_az

                delta_az = abs(start_az - end_az)

                if delta_az >= 180:
                    large_angle = delta_az
                    small_angle = 360 - delta_az
                elif delta_az < 180:
                    small_angle = delta_az
                    large_angle = 360 - delta_az

                if self.arc_chosen == "short":
                    angle = small_angle
                elif self.arc_chosen == "long":
                    angle = large_angle

                angle_feat = QgsFeature()
                angle_feat.setGeometry(self.final_arc.segmentize(0.1))

                angle_value = angle
                angle_feat.setAttributes(["Sudut", str(angle_value)])

                self.dimension_layer_prov = self.dimension_layer.dataProvider()
                self.dimension_layer.startEditing()
                self.dimension_layer_prov.addFeatures([angle_feat])
                self.dimension_layer.commitChanges()

                # try:
                #     self.vm_center.hide()
                #     self.vm_1.hide()
                #     self.vm_2.hide()
                #     self.geomrb_short_arc.hide()
                #     self.geomrb_long_arc.hide()
                # except:
                #     pass

                self.click_counter = 0

        elif event.button() == QtCore.Qt.RightButton:
            try:
                self.canvas.scene().removeItem(self.vm_center)
                self.canvas.scene().removeItem(self.vm_1)
                self.canvas.scene().removeItem(self.vm_2)
                self.canvas.scene().removeItem(self.rb_buffer)
                self.canvas.scene().removeItem(self.geomrb_buffer)
                self.canvas.scene().removeItem(self.geomrb_short_arc)
                self.canvas.scene().removeItem(self.geomrb_long_arc)
            except NameError:
                pass

            self.completed.emit()

    def check_arc(self, point_check, short_arc, long_arc):
        a1, b1, c1, d1 = short_arc.closestSegment(point_check)
        a2, b2, c2, d2 = long_arc.closestSegment(point_check)

        if a1 < a2:
            arc_highlight(self.geomrb_short_arc)
            arc_dehighlight(self.geomrb_long_arc)
            self.arc_chosen = "short"
            return short_arc
        elif a1 > a2:
            arc_highlight(self.geomrb_long_arc)
            arc_dehighlight(self.geomrb_short_arc)
            self.arc_chosen = "long"
            return long_arc


# ----------------------------------------------------------- #
#                     Distance Dimension                      #
# ----------------------------------------------------------- #
class DimensionDistanceTool(QgsMapTool):

    completed = pyqtSignal()

    def __init__(self, canvas, dimension_layer):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        self.dimension_layer = dimension_layer

        enable_snapping()

        self.vm_1 = create_vertex_marker(self.canvas, "CROSS")
        self.vm_2 = create_vertex_marker(self.canvas, "CIRCLE")

        self.rb_draw = create_rubberband(self.canvas)
        self.rb_main = create_rubberband(self.canvas)
        self.rb_start = create_rubberband(self.canvas, "DASH_LINE")
        self.rb_end = create_rubberband(self.canvas, "DASH_LINE")

        self.list_vm = []
        self.list_vm.append(self.vm_1)
        self.list_vm.append(self.vm_2)

        self.click_counter = 0

    def canvasMoveEvent(self, event):
        point_snap, _ = snapping_point(self.canvas, event.pos())
        if self.click_counter == 0:  # proceed to add start point
            self.vm_1.setCenter(point_snap)

        elif self.click_counter == 1:  # proceed to add end point
            self.vm_2.setCenter(point_snap)
            list_point = [self.start_point, point_snap]
            draw_geom = QgsGeometry().fromPolylineXY(list_point)
            self.rb_draw.setToGeometry(draw_geom)

        elif self.click_counter == 2:  # proceed to start offsetting
            p = self.canvas.getCoordinateTransform().toMapCoordinates(event.pos())
            sqrdist, pt, nid, side = self.main_geom.closestSegmentWithContext(p)
            dist = math.sqrt(sqrdist)
            self.offset_geom = self.main_geom.offsetCurve(-side * dist, 6, 1, 1)
            _, offset_start, _, _ = self.offset_geom.closestSegmentWithContext(
                self.start_point
            )
            _, offset_end, _, _ = self.offset_geom.closestSegmentWithContext(
                self.end_point
            )
            start_point_list = [self.start_point, offset_start]
            end_point_list = [self.end_point, offset_end]
            self.start_geom = QgsGeometry.fromPolylineXY(start_point_list)
            self.end_geom = QgsGeometry.fromPolylineXY(end_point_list)
            self.rb_start.setToGeometry(self.start_geom)
            self.rb_end.setToGeometry(self.end_geom)
            self.rb_main.setToGeometry(self.offset_geom)

    def canvasReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.click_counter += 1
            self.point_snap, _ = snapping_point(self.canvas, event.pos())

            if self.click_counter == 1:  # indicates finished adding first point
                self.vm_1.setCenter(self.point_snap)
                self.start_point = self.point_snap

            elif self.click_counter == 2:  # indicates finished adding second point
                self.vm_2.setCenter(self.point_snap)
                self.end_point = self.point_snap
                list_point_main = [self.start_point, self.end_point]
                self.main_geom = QgsGeometry().fromPolylineXY(list_point_main)
                self.rb_main.setToGeometry(self.main_geom)

            elif self.click_counter == 3:  # indicates finished offsetting line
                start_feat = QgsFeature()
                start_feat.setGeometry(self.start_geom)
                start_feat.setAttributes(["-", "-"])

                end_feat = QgsFeature()
                end_feat.setGeometry(self.end_geom)
                end_feat.setAttributes(["-", "-"])

                offset_feat = QgsFeature()
                offset_feat.setGeometry(self.offset_geom)
                distance_value = round(self.offset_geom.length(), 3)
                offset_feat.setAttributes(["Jarak", str(distance_value)])

                result_feat = [start_feat, end_feat, offset_feat]

                self.dimension_layer_prov = self.dimension_layer.dataProvider()
                self.dimension_layer.startEditing()
                self.dimension_layer_prov.addFeatures(result_feat)
                self.dimension_layer.commitChanges()

                self.click_counter = 0

        elif event.button() == QtCore.Qt.RightButton:
            try:
                self.canvas.scene().removeItem(self.vm_1)
                self.canvas.scene().removeItem(self.vm_2)
                self.canvas.scene().removeItem(self.rb_draw)
                self.canvas.scene().removeItem(self.rb_main)
                self.canvas.scene().removeItem(self.rb_start)
                self.canvas.scene().removeItem(self.rb_end)
            except Exception:
                pass
            self.completed.emit()


def snapping_point(canvas, point):
    map_coord = canvas.getCoordinateTransform().toMapCoordinates(point)
    snapped = canvas.snappingUtils().snapToMap(point)

    if snapped.isValid():
        return snapped.point(), snapped.isValid()
    else:
        return map_coord, snapped.isValid()


def create_vertex_marker(canvas, type="BOX"):
    vm = QgsVertexMarker(canvas)

    if type == "BOX":
        icon_type = QgsVertexMarker.ICON_BOX
    elif type == "CIRCLE":
        icon_type = QgsVertexMarker.ICON_CIRCLE
    elif type == "CROSS":
        icon_type = QgsVertexMarker.ICON_CROSS
    else:
        icon_type = QgsVertexMarker.ICON_X

    vm.setIconType(icon_type)
    vm.setPenWidth(3)
    vm.setIconSize(7)
    return vm


def create_rubberband(canvas, line_style="SOLID_LINE"):
    rb = QgsRubberBand(canvas, False)
    rb.setStrokeColor(QtGui.QColor(128, 128, 128, 180))  # grey
    rb.setFillColor(QtGui.QColor(0, 0, 0, 0))
    rb.setWidth(1)
    if line_style == "DASH_LINE":
        rb.setLineStyle(QtCore.Qt.DashLine)
    elif line_style == "SOLID_LINE":
        rb.setLineStyle(QtCore.Qt.SolidLine)
    elif line_style == "DOT_LINE":
        rb.setLineStyle(QtCore.Qt.DotLine)
    return rb


def create_geom_rubberband(canvas, line_style="SOLID_LINE"):
    # QgsGeometryRubberBand allows the usage of circular string so that it will
    # be possible to draw circle without using buffer function

    rb = QgsGeometryRubberBand(canvas, False)
    rb.setStrokeColor(QtGui.QColor(128, 128, 128, 180))  # grey
    rb.setFillColor(QtGui.QColor(0, 0, 0, 0))
    rb.setVertexDrawingEnabled(False)
    rb.setStrokeWidth(1)
    if line_style == "DASH_LINE":
        rb.setLineStyle(QtCore.Qt.DashLine)
    elif line_style == "SOLID_LINE":
        rb.setLineStyle(QtCore.Qt.SolidLine)
    elif line_style == "DOT_LINE":
        rb.setLineStyle(QtCore.Qt.DotLine)
    return rb


def arc_highlight(arc):
    arc.setStrokeWidth(2)
    arc.setStrokeColor(QtGui.QColor(100, 100, 100, 180))


def arc_dehighlight(arc):
    arc.setStrokeWidth(1)
    arc.setStrokeColor(QtGui.QColor(128, 128, 128, 180))


def snapping_config():
    config = QgsSnappingConfig()
    config.setType(QgsSnappingConfig.VertexAndSegment)
    config.setUnits(QgsTolerance.Pixels)
    config.setTolerance(15)
    config.setIntersectionSnapping(True)
    config.setMode(QgsSnappingConfig.AllLayers)
    return config


def enable_snapping(value=True):
    config = snapping_config()
    config.setEnabled(value)
    QgsProject.instance().setSnappingConfig(config)
