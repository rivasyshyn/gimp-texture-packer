#!/usr/bin/python

from gimpfu import *
import os
import json

lua_table = """
-- local sheetInfo = require("mysheet")
-- local myImageSheet = graphics.newImageSheet( "mysheet.png", sheetInfo:getSheet() )
-- local sprite = display.newSprite( myImageSheet , { frames={sheetInfo:getFrameIndex("sprite")} } )
--
						
local SheetInfo = {}
						
SheetInfo.sheet =
{
	frames = {
%s
	},
%s
}
						
SheetInfo.frameIndex =
{
%s
}

function SheetInfo:getSheet()
  return self.sheet;
end

function SheetInfo:getFrameIndex(name)
  return self.frameIndex[name];
end

return SheetInfo
"""
lua_frame = """		{
		-- %s
		  x=%s,
			y=%s,
			width=%s,
			height=%s,
		},
"""
lua_size =  """	sheetContentWidth = %s,
	sheetContentHeight = %s
"""
lua_frame_index = """		["%s"] = %s,
"""

class PackNode(object):
  """
  Creates an area which can recursively pack other areas of smaller sizes into itself.
  """
  def __init__(self, area):
    #if tuple contains two elements, assume they are width and height, and origin is (0,0)
    if len(area) == 2:
        area = (0,0,area[0],area[1])
    self.area = area

  def __repr__(self):
    return "<%s %s>" % (self.__class__.__name__, str(self.area))

  def get_width(self):
    return self.area[2] - self.area[0]
  width = property(fget=get_width)

  def get_height(self):
    return self.area[3] - self.area[1]
  height = property(fget=get_height)

  def get_x(self):
		return self.area[0]
  x = property(fget=get_x)

  def get_y(self):
  	return self.area[1]
  y = property(fget=get_y)

  def insert(self, area, padding):
    if hasattr(self, 'child'):
      a = self.child[0].insert(area, padding)
      if a is None: return self.child[1].insert(area, padding)
      return a

    area = PackNode(area)
    if area.width <= self.width and area.height <= self.height:
      self.child = [None,None]
      self.child[0] = PackNode((self.area[0]+area.width+padding, self.area[1]+padding, self.area[2], self.area[1] + area.height))
      self.child[1] = PackNode((self.area[0]+padding, self.area[1]+area.height+padding, self.area[2], self.area[3]))
      return PackNode((self.area[0], self.area[1], self.area[0]+area.width, self.area[1]+area.height))


def output_lua(atlas_pack, img):
	size = lua_size % (img.width, img.height)

	frames = ''
	frames_indexes = ''
	index = 1
	for pack, layer in atlas_pack:
		frames += (lua_frame % (layer.name, pack.x, pack.y, pack.width, pack.height))
		frames_indexes += (lua_frame_index % (layer.name, index))
		index += 1

	return lua_table % (frames, size, frames_indexes)

def output_json(atlas_pack):
	jp = {}
	for pack, layer in atlas_pack:
		jp[str(layer.name)] = {
			'x': pack.x,
			'y': pack.y,
			'width': pack.width,
			'height': pack.height
		}

	return json.dumps(jp)


def get_output_file(output, filename):
	path = None
	if os.path.isdir(output):
		path = os.path.join(output, filename)
	else:
		path = os.path.join(os.path.expanduser("~"), filename)
	return path


def tp_plugin_main(timg, tdrawable, max_width, max_height, padding, autocrop, output):
	img = gimp.Image(int(max_width), int(max_height), RGB)

	tree = PackNode((max_width, max_height))
	layers_pack = []
	layers = sorted([(layer.width * layer.height, layer) for layer in filter(lambda l: l.visible > 0, timg.layers)], reverse=True)
	success = True

	for _, layer in layers:
		cp_layer = pdb.gimp_layer_new_from_drawable(layer, img)
		pdb.gimp_image_insert_layer(img, cp_layer, None, -1)
		pdb.plug_in_autocrop_layer(img, cp_layer)
		cp_layer.name = layer.name
		lpack = tree.insert((cp_layer.width, cp_layer.height), int(padding))
		if lpack is None: 
			success = False
			break
		layers_pack.append((lpack, layer))
		cp_layer.set_offsets(0, 0)
		cp_layer.translate(lpack.x, lpack.y)

	pdb.script_fu_reverse_layers(img, None)

	# in case all layers inserted into atlas complit by mergin layers and autocrop if requested
	if success:
		pdb.gimp_image_merge_visible_layers(img, CLIP_TO_IMAGE)
		if(autocrop):
			pdb.plug_in_autocrop(img, img.active_layer)

	# output JSON
	jp = output_json(layers_pack)
	pdb.gimp_message(jp)
	file = open(get_output_file(output, "texturepack.json"), 'w')
	file.write(jp)
	file.close()

	# output lua
	lp = output_lua(layers_pack, img)
	pdb.gimp_message(lp)
	file = open(get_output_file(output, "texturepack.lua"), 'w')
	file.write(lp)
	file.close()
	
	gimp.Display(img)
	gimp.displays_flush()


register(
				"python_fu_texture_packer",
				"Pack all Layers as TextureAtlas",
				"Pack all Layers as TextureAtlas",
				"Roman Ivasyshyn",
				"Roman Ivasyshyn",
				"2018",
				"TexutrePacker",
				"RGB*,GRAY*",
				[
					(PF_IMAGE, "image", "Input image", None),
					(PF_DRAWABLE, "drawable", "Input drawable", None),
					(PF_SPINNER, "atlas_width", "Max Atlas Width", 512, (1, 10000, 1)),
					(PF_SPINNER, "atlas_height", "Max Atlas Height", 512, (1, 10000, 1)),
					(PF_SPINNER, "texture_padding", "Texture Padding", 2, (0, 100, 1)),
					(PF_BOOL, "avtocrop", "Avtocrop", False),
					(PF_DIRNAME, "output", "Otput Atlas JSON to:", None),
				],
				[],
				tp_plugin_main, menu="<Image>/Filters")

main()