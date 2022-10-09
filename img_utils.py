import cv2


def stream_to_imgs(capture):
    """
    Return an iterator to the images in a given OpenCV
    VideoCapture stream. Involves IO.

    Parameter:
    capture : OpenCV VideoCapture stream, must stay opened.
    """
    # Frames can only be extracted if the video capture
    # stream is opened.
    assert capture.isOpened(), "Error opening VideoCapture stream."

    # Extract frames until the stream is exhausted.
    while True:
        success, image = capture.read()
        if not success:
            break
        yield image


def imgs_to_vid(filename, dims, fps, images):
    """
    Parameters:
    filename : The name of the video output, must ends with ".mp4".
    dims     : A tuple (width, height) specifying the video dimensions.
    fps      : Frames per second.
    images   : An iterator to OpenCV Mat image objects.
    """
    # Function limitation: can only output videos in mp4 codec.
    assert filename.endswith(".mp4"), "Attempted to output non mp4-codec video."

    # Create a OpenCV VideoWriter object as IO wrapper.
    writer = cv2.VideoWriter(
        filename,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        dims
    )

    # Write the image into the video container.
    for image in images:
        writer.write(image)

    # Clean up to prevent memory leaks.
    writer.release()
