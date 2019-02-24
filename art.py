# -*- coding: utf-8 -*-
# This file is part of vizop. Copyright xSeriCon, 2017
"""Code to deal with artwork for the GUI.

"""

import wx, os.path, warnings, copy

import vizop_misc, info


class ArtProvider(wx.ArtProvider):
	"""ArtProvider class for providing vizop with images/icons.

	"""
	def __init__(self):
		wx.ArtProvider.__init__(self)

		# build a mapping between image/logo/icon names and their filenames
		# The keys are just the filenames without the extension, and the
		# values are the complete path to the image file
		self.images = {}
		icon_dir = os.path.join(vizop_misc.get_sys_runtime_files_dir(), info.IconFolderTail)
		for root, dirs, files in os.walk(icon_dir, followlinks=True):
			for f_name in files:
				self.images[os.path.splitext(f_name)[0]] = os.path.join(root, f_name)

	def ImageCatalogue(self, OnlyWithPrefix=''): # return list of all available image names
		# if OnlyWithPrefix is a non-empty string, only images starting with that prefix will be returned
		assert isinstance(OnlyWithPrefix, str)
		return [i for i in self.images if i.startswith(OnlyWithPrefix)]

	def CreateBitmap(self, artid, client, size):
		"""
		Overrides base class CreateBitmap method, to provide our own icons rather than
		the system ones.

		Returns a wxBitmap instance, or wxNullBitmap if the image cannot be found.
		"""
		if size.width == -1:
			sizerq = wx.ArtProvider.GetSizeHint(client)

			if sizerq.width == -1:
				#GetSizeHint seems to fail if GetIcon was called and in this
				#case we want a size of 64
				sizerq = wx.Size(64,64)

		else:
			sizerq = size.width

		bmp = wx.BitmapFromImage(self.get_image(artid, (sizerq, sizerq),
												conserve_aspect_ratio=False))
		return bmp


	def get_image(self, name, size, conserve_aspect_ratio=False):
		"""Load and return the requested image at the requested size.

		This method will search <prefix>/icons for image files, where <prefix>
		is the path returned by vizop_misc.get_sys_runtime_files_dir().

		   * name - the name of the requested image. This should be the filename
					without the extension.

		   * size - tuple (width, height) you want the returned image to be, or None to return it at the same size
					as the source file.

		   * conserve_aspect_ratio - if set to False, then you will get an image of
									 exactly the size you ask for. If True, then you
									 will get an image back which is as close to the
									 size you requested as possible but which preserves
									 the aspect ratio of the original file.

		Returns a wxImage object. If the requested image cannot be found/loaded then
		wx.NullImage is returned.
		"""
		try:
			filename = self.images[name]
			im = wx.Image(filename, wx.BITMAP_TYPE_ANY)
		except KeyError:
			warnings.warn(_("Failed to load image \'%s\'. No matching file found" % name))
			return wx.NullImage

		if size is not None: # rescale to size, if specified
			if conserve_aspect_ratio:
				#find the size closest to that requested which keeps the aspect ratio of
				#the original image.
				orig_x = im.GetWidth()
				orig_y = im.GetHeight()
				scale_factor = min(size[0] * 1.0 / orig_x, size[1] * 1.0 / orig_y)
				size = (round(orig_x * scale_factor), round(orig_y * scale_factor))
			im.Rescale(*size) # resize to fit space
		return im

def ZoomedImage(UnzoomedImage, Zoom=1.0, Quality=wx.IMAGE_QUALITY_NORMAL):
	# return UnzoomedImage (wx.Image object) rescaled to Zoom (int or float)
	# Don't use; it damages the original UnzoomedImage
	assert isinstance(Zoom, (int, float))
	orig_x = UnzoomedImage.GetWidth() # get unzoomed dimensions
	orig_y = UnzoomedImage.GetHeight()
	UnzoomedImageCopy = copy.copy(UnzoomedImage)
	return UnzoomedImageCopy.Rescale(round(orig_x * Zoom), round(orig_y * Zoom), quality=Quality)
