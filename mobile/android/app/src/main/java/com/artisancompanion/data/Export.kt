package com.artisancompanion.data

import java.io.File
import java.io.FileOutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/** File export helpers (Settings → Data). All work is local; nothing leaves the device. */
object Export {

    /**
     * Zip [sourceDir] (recursively) into [destFile].
     * Returns false when there is nothing to export (missing/empty folder).
     */
    fun zipDirectory(sourceDir: File, destFile: File): Boolean {
        if (!sourceDir.isDirectory) return false
        val files = sourceDir.walkTopDown().filter { it.isFile }.toList()
        if (files.isEmpty()) return false
        destFile.parentFile?.mkdirs()
        ZipOutputStream(FileOutputStream(destFile)).use { zip ->
            files.forEach { file ->
                val entryName = file.relativeTo(sourceDir).invariantSeparatorsPath
                zip.putNextEntry(ZipEntry(entryName))
                file.inputStream().use { it.copyTo(zip) }
                zip.closeEntry()
            }
        }
        return true
    }
}
