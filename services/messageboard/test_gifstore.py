import base64
import io
import tempfile
import unittest
from PIL import Image
from gifstore import GifStore


def upload_data(color="red", fit="fit"):
    out=io.BytesIO()
    Image.new("RGB",(20,20),color).save(out,format="GIF",save_all=True,
        append_images=[Image.new("RGB",(20,20),"blue")],duration=[100,200],loop=0)
    return {"data":base64.b64encode(out.getvalue()).decode(),"name":"example.gif","fit":fit}


class GifTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.store=GifStore(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def test_rotation_restart_order_and_removal(self):
        self.store.upload(upload_data())
        self.store.upload(upload_data("green"))
        first=self.store.next()["frames"]
        second=GifStore(self.temp.name).next()["frames"]
        self.assertNotEqual(first[0],second[0])
        self.assertEqual(GifStore(self.temp.name).next()["frames"],first)
        ident=self.store.listing()["items"][1]["id"]
        self.store.change({"action":"up","id":ident})
        self.assertEqual(self.store.next()["frames"],second)
        self.store.change({"action":"remove","id":ident})
        self.assertEqual(len(self.store.listing()["items"]),1)
    def test_fit_crop_and_duration(self):
        for fit in ["fit","crop"]:
            item=self.store.upload(upload_data(fit=fit))["items"][-1]
            frames=self.store.frames(item["id"])
            im=Image.open(io.BytesIO(base64.b64decode(frames[0]))).convert("RGB")
            self.assertEqual(im.size,(64,32))
            self.assertEqual(im.getpixel((0,0)),(0,0,0) if fit=="fit" else (255,0,0))
            self.assertNotEqual(frames[0],frames[1])
            self.assertEqual(frames[0],frames[2])
            for seconds in [5,10,15]:
                self.store.change({"action":"duration","seconds":seconds})
                self.assertEqual(sum(self.store.playback(item["id"])[1]),seconds*1000)
            preview=Image.open(io.BytesIO(self.store.preview(item["id"])))
            self.assertEqual(preview.size,(64,32))
    def test_invalid_upload_and_path(self):
        for payload in [{}, {"fit":"fit","data":"!!!!"}, {"fit":"stretch","data":""}]:
            with self.assertRaises(ValueError):self.store.upload(payload)
        with self.assertRaises(ValueError):self.store.preview("../playlist")
        with self.assertRaises(ValueError):self.store.change({"action":"duration","seconds":999})
        self.assertEqual(self.store.next()["frames"],[])
    def test_invalid_format(self):
        out=io.BytesIO();Image.new("RGB",(10,10)).save(out,format="PNG")
        with self.assertRaises(ValueError):
            self.store.upload({"fit":"fit","data":base64.b64encode(out.getvalue()).decode()})

    def test_original_timing_and_legacy_migration(self):
        item = self.store.upload(upload_data())["items"][0]
        frames, durations = self.store.playback(item["id"])
        self.assertEqual(durations[:4], [100, 200, 100, 200])
        import json
        path = self.store.folder / (item["id"] + ".json")
        path.write_text(json.dumps([frames[0]]))
        self.assertEqual(self.store.playback(item["id"])[1][:4], [100, 200, 100, 200])
        result = self.store.next()
        self.assertEqual(sum(result["holds"]) * result["delay"], 10000)

    def test_browser_short_delay_fallback(self):
        for delay in [0, 10, 20, 70, 250]:
            out = io.BytesIO()
            Image.new("RGB", (8,8), "red").save(out, format="GIF", save_all=True,
                append_images=[Image.new("RGB", (8,8), "blue")], duration=[delay,300])
            data = self.store.convert(out.getvalue(), "fit")
            self.assertEqual(data["durations"], [100 if delay < 20 else delay, 300])
