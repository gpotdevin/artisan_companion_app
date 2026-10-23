package com.artisancompanion.data

import android.content.ContentResolver
import android.net.Uri
import android.provider.OpenableColumns
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream

/**
 * Copies user-picked .alog files (via the Storage Access Framework) into the
 * app's logs directory so the Python core can index them by real filesystem
 * path. v1 keeps the core untouched; a future version can read SAF trees
 * directly without copying.
 */
object FileImport {

    /** Copy each picked [uris] into [destDir], returning the count copied. */
    suspend fun copyInto(resolver: ContentResolver, uris: List<Uri>, destDir: File): Int =
        withContext(Dispatchers.IO) {
            destDir.mkdirs()
            var count = 0
            for (uri in uris) {
                val name = displayName(resolver, uri) ?: continue
                if (!name.endsWith(".alog", ignoreCase = true)) continue
                val target = File(destDir, name)
                resolver.openInputStream(uri)?.use { input ->
                    FileOutputStream(target).use { output -> input.copyTo(output) }
                } ?: continue
                count++
            }
            count
        }

    private fun displayName(resolver: ContentResolver, uri: Uri): String? =
        resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
            if (c.moveToFirst()) c.getString(0) else null
        }
}
