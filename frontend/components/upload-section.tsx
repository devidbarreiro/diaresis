"use client"

import { useState, useCallback } from "react"
import { useDropzone } from "react-dropzone"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Upload, FileAudio, Loader2, AlertCircle } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { Alert, AlertDescription } from "@/components/ui/alert"

interface UploadSectionProps {
  onUploadSuccess: () => void
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://51.91.166.216:5000"

export function UploadSection({ onUploadSuccess }: UploadSectionProps) {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { toast } = useToast()

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0])
      setError(null)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "audio/*": [".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"],
      "video/*": [".mp4", ".mov", ".avi", ".mkv"],
    },
    maxFiles: 1,
  })

  const handleUpload = async () => {
    if (!file) return

    setUploading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append("file", file)

      console.log("[v0] Enviando archivo:", file.name, "Tamaño:", (file.size / 1024 / 1024).toFixed(2), "MB")

      const response = await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Error ${response.status}: ${errorText}`)
      }

      const data = await response.json()
      console.log("[v0] Datos recibidos:", data)

      toast({
        title: "¡Archivo subido exitosamente!",
        description: `ID del trabajo: ${data.job_id}`,
      })

      setFile(null)
      onUploadSuccess()
    } catch (error) {
      console.error("[v0] Error al subir archivo:", error)

      const errorMessage = error instanceof Error ? error.message : "Error desconocido"

      setError(errorMessage)

      toast({
        title: "Error al subir archivo",
        description: errorMessage,
        variant: "destructive",
      })
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="space-y-4">
      {error && (
        <Alert variant="destructive" className="border-2">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            <strong>Error:</strong> {error}
          </AlertDescription>
        </Alert>
      )}

      <Card className="border-4 border-primary">
        <CardHeader className="bg-card">
          <CardTitle className="font-mono text-xl uppercase">Subir Audio</CardTitle>
          <CardDescription>Sube tu archivo de audio o video para separar las voces</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 pt-6">
          <div
            {...getRootProps()}
            className={`cursor-pointer rounded-lg border-4 border-dashed border-primary p-12 text-center transition-colors ${
              isDragActive ? "bg-muted" : "bg-card hover:bg-muted"
            }`}
          >
            <input {...getInputProps()} />
            <div className="flex flex-col items-center gap-4">
              {file ? (
                <>
                  <FileAudio className="h-12 w-12 text-primary" />
                  <div>
                    <p className="font-mono font-semibold text-foreground">{file.name}</p>
                    <p className="text-sm text-muted-foreground">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                  </div>
                </>
              ) : (
                <>
                  <Upload className="h-12 w-12 text-primary" />
                  <div>
                    <p className="font-mono font-semibold text-foreground">Arrastra y suelta un archivo aquí</p>
                    <p className="text-sm text-muted-foreground">o haz clic para seleccionar (MP4, WAV, MP3, etc.)</p>
                  </div>
                </>
              )}
            </div>
          </div>

          {file && (
            <Button
              onClick={handleUpload}
              disabled={uploading}
              className="w-full bg-black py-7 font-mono text-xl font-bold uppercase tracking-wide text-white hover:bg-black/90"
              size="lg"
            >
              {uploading ? (
                <>
                  <Loader2 className="mr-3 h-6 w-6 animate-spin" />
                  Procesando...
                </>
              ) : (
                <>
                  <Upload className="mr-3 h-6 w-6" />
                  Enviar Audio
                </>
              )}
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
