const assert = require("node:assert/strict");
const test = require("node:test");
const { readdir, readFile, stat } = require("node:fs/promises");
const path = require("node:path");
const { createHash } = require("node:crypto");
const sharp = require("sharp");

const ambient = path.resolve(__dirname, "../public/brand/ambient");
const home = path.resolve(__dirname, "../public/brand/home");

test("all photographic derivatives are metadata-free, optimized local web formats", async () => {
  for (const directory of [ambient, home]) {
    for (const file of await readdir(directory)) {
      assert.match(file, /\.(avif|webp)$/);
      const target = path.join(directory, file);
      const metadata = await sharp(target).metadata();
      for (const field of ["exif", "xmp", "iptc", "icc", "orientation"]) {
        assert.equal(metadata[field], undefined, `${file}: unexpected ${field}`);
      }
      const budget = file.includes("mobile") ? 150 * 1024 : 300 * 1024;
      assert.ok((await stat(target)).size <= budget, `${file}: exceeds size budget`);
      assert.ok(metadata.width > 0 && metadata.height > 0);
    }
  }
});

test("asset hashes and dimensions agree with the committed crop/provenance manifest", async () => {
  const manifest = JSON.parse(await readFile(path.resolve(__dirname, "../../docs/photo-ambient-asset-manifest.json"), "utf8"));
  assert.equal(manifest.length, 24);
  for (const row of manifest) {
    const target = path.join(ambient, row.file);
    const data = await readFile(target);
    assert.equal(createHash("sha256").update(data).digest("hex"), row.sha256, row.file);
    const metadata = await sharp(data).metadata();
    assert.deepEqual([metadata.width, metadata.height], row.dimensions, row.file);
    assert.equal(data.length, row.bytes, row.file);
  }
});
