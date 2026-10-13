#!/usr/bin/env node

import { readFileSync, writeFileSync } from "node:fs";

const [inputPath, outputPath, baseText = "0x60020000", entryText] = process.argv.slice(2);
if (!inputPath || !outputPath) {
  throw new Error("usage: wrap-arm-elf.mjs INPUT OUTPUT [BASE]");
}

const payload = readFileSync(inputPath);
const base = Number.parseInt(baseText, 0);
const entry = entryText === undefined ? (base | 1) >>> 0 : Number.parseInt(entryText, 0) >>> 0;
const payloadOffset = 0x1000;
const header = Buffer.alloc(payloadOffset);

// ELF32 little-endian executable, ARM EABI, one read/execute PT_LOAD segment.
header.set([0x7f, 0x45, 0x4c, 0x46, 1, 1, 1, 0], 0);
header.writeUInt16LE(2, 16); // ET_EXEC
header.writeUInt16LE(40, 18); // EM_ARM
header.writeUInt32LE(1, 20); // EV_CURRENT
header.writeUInt32LE(entry, 24); // Cortex-M reset vector, including Thumb bit
header.writeUInt32LE(52, 28); // program header offset
header.writeUInt32LE(0, 32); // no section table
header.writeUInt32LE(0x05000000, 36); // EABI version 5
header.writeUInt16LE(52, 40); // ELF header size
header.writeUInt16LE(32, 42); // program header entry size
header.writeUInt16LE(1, 44); // one program header

header.writeUInt32LE(1, 52); // PT_LOAD
header.writeUInt32LE(payloadOffset, 56);
header.writeUInt32LE(base >>> 0, 60);
header.writeUInt32LE(base >>> 0, 64);
header.writeUInt32LE(payload.length, 68);
header.writeUInt32LE(payload.length, 72);
header.writeUInt32LE(5, 76); // PF_R | PF_X
header.writeUInt32LE(0x1000, 80);

writeFileSync(outputPath, Buffer.concat([header, payload]));
