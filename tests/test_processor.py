"""Tests for image processing functionality"""

import io

import pytest
from PIL import Image

from src.services.processor import ImageProcessor


@pytest.fixture
def processor():
    """Create an ImageProcessor instance"""
    return ImageProcessor()


@pytest.fixture
def sample_image_bytes():
    """Create a sample image as bytes"""
    img = Image.new("RGB", (2048, 2048), color="red")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    return img_bytes.getvalue()


def test_image_resize(processor, sample_image_bytes):
    """Test image resizing to different dimensions"""
    # Resize to 1024x1024
    resized = processor.resize(sample_image_bytes, 1024, 1024)

    # Verify
    result_img = Image.open(io.BytesIO(resized))
    assert result_img.size == (1024, 1024)
    assert result_img.format == "PNG"


def test_image_resize_portrait(processor, sample_image_bytes):
    """Test resizing to portrait aspect ratio"""
    resized = processor.resize(sample_image_bytes, 1080, 1920)

    result_img = Image.open(io.BytesIO(resized))
    assert result_img.size == (1080, 1920)


def test_image_resize_landscape(processor, sample_image_bytes):
    """Test resizing to landscape aspect ratio"""
    resized = processor.resize(sample_image_bytes, 1920, 1080)

    result_img = Image.open(io.BytesIO(resized))
    assert result_img.size == (1920, 1080)


def test_add_text_overlay(processor, sample_image_bytes):
    """Test adding text overlay to image"""
    text = "Test Campaign Message"

    result = processor.add_text_overlay(
        image_data=sample_image_bytes, text=text, position="bottom"
    )

    # Verify result is valid image
    result_img = Image.open(io.BytesIO(result))
    assert result_img.size == (2048, 2048)
    assert result_img.mode == "RGBA"  # Should have alpha channel


def test_add_text_overlay_different_positions(processor, sample_image_bytes):
    """Test text overlay at different positions"""
    positions = ["bottom", "center", "top"]

    for position in positions:
        result = processor.add_text_overlay(
            image_data=sample_image_bytes, text="Test", position=position
        )

        # Should produce valid image
        result_img = Image.open(io.BytesIO(result))
        assert result_img.size == (2048, 2048)
