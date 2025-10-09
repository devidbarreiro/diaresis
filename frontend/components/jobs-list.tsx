"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Download, Loader2, CheckCircle2, XCircle, Clock, AlertCircle } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { Alert, AlertDescription } from "@/components/ui/alert"

interface Job {
  id: string
  filename: string
  status: "queued" | "processing" | "completed" | "failed"
  progress: number
  result?: {
    speakers_detected: number
    processing_time: number
    output_files: string[]
  }
  error?: string
}

interface JobsListProps {
  refreshTrigger: number
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://51.91.166.216:5000"

export function JobsList({ refreshTrigger }: JobsListProps) {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { toast } = useToast()

  const fetchJobs = async () => {
    try {
      console.log("[v0] Obteniendo trabajos desde proxy")

      const response = await fetch("/api/proxy/jobs")

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || `Error ${response.status}`)
      }

      const data = await response.json()
      console.log("[v0] Trabajos recibidos:", data)

      setJobs(data.jobs || [])
      setError(null)
    } catch (err) {
      console.error("[v0] Error al obtener trabajos:", err)

      const errorMessage = err instanceof Error ? err.message : "Error desconocido"

      setError(errorMessage)

      toast({
        title: "Error de conexión",
        description: errorMessage,
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchJobs()
  }, [refreshTrigger])

  useEffect(() => {
    const interval = setInterval(() => {
      const hasActiveJobs = jobs.some((job) => job.status === "queued" || job.status === "processing")
      if (hasActiveJobs) {
        console.log("[v0] Actualizando trabajos activos...")
        fetchJobs()
      }
    }, 3000)

    return () => clearInterval(interval)
  }, [jobs])

  const downloadSpeaker = async (jobId: string, speakerId: number, filename: string) => {
    try {
      console.log("[v0] Descargando hablante:", speakerId, "del trabajo:", jobId)

      const response = await fetch(`/api/proxy/job/${jobId}/download/${speakerId}`)

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Error ${response.status}: ${errorText}`)
      }

      const blob = await response.blob()

      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `${filename}_speaker_${speakerId + 1}.wav`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      toast({
        title: "Descarga iniciada",
        description: `Hablante ${speakerId + 1}`,
      })
    } catch (error) {
      console.error("[v0] Error al descargar:", error)

      toast({
        title: "Error al descargar",
        description: error instanceof Error ? error.message : "Error desconocido",
        variant: "destructive",
      })
    }
  }

  const getStatusIcon = (status: Job["status"]) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 className="h-5 w-5 text-green-600" />
      case "failed":
        return <XCircle className="h-5 w-5 text-destructive" />
      case "processing":
        return <Loader2 className="h-5 w-5 animate-spin text-accent" />
      case "queued":
        return <Clock className="h-5 w-5 text-muted-foreground" />
    }
  }

  const getStatusBadge = (status: Job["status"]) => {
    const variants: Record<Job["status"], "default" | "secondary" | "destructive" | "outline"> = {
      completed: "default",
      failed: "destructive",
      processing: "secondary",
      queued: "outline",
    }
    const labels: Record<Job["status"], string> = {
      completed: "completado",
      failed: "fallido",
      processing: "procesando",
      queued: "en cola",
    }
    return (
      <Badge variant={variants[status]} className="font-mono uppercase">
        {labels[status]}
      </Badge>
    )
  }

  if (loading) {
    return (
      <Card className="border-4 border-primary">
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive" className="border-2">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription className="space-y-2">
          <div>
            <strong>Error al cargar trabajos:</strong> {error}
          </div>
          {error.includes("conectar a la API") && (
            <div className="mt-2 text-xs">
              <p className="font-semibold">Posibles soluciones:</p>
              <ul className="ml-4 mt-1 list-disc space-y-1">
                <li>Verifica que el servidor esté corriendo en http://51.91.166.216:5000</li>
                <li>Asegúrate de que CORS esté configurado para permitir peticiones desde este dominio</li>
                <li>Verifica que el firewall permita conexiones al puerto 5000</li>
              </ul>
            </div>
          )}
        </AlertDescription>
      </Alert>
    )
  }

  if (jobs.length === 0) {
    return (
      <Card className="border-4 border-primary">
        <CardHeader className="bg-card">
          <CardTitle className="font-mono text-xl uppercase">Tus Trabajos</CardTitle>
          <CardDescription>Rastrea el estado del procesamiento y descarga los resultados</CardDescription>
        </CardHeader>
        <CardContent className="py-12 text-center">
          <p className="text-muted-foreground">No hay trabajos aún. ¡Sube un archivo para comenzar!</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="font-mono text-xl font-bold uppercase text-foreground">Tus Trabajos</h2>
        <p className="text-sm text-muted-foreground">Rastrea el estado del procesamiento y descarga los resultados</p>
      </div>

      {jobs.map((job) => (
        <Card key={job.id} className="border-4 border-primary">
          <CardHeader className="bg-card">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <CardTitle className="font-mono text-lg">{job.filename}</CardTitle>
                <CardDescription className="font-mono text-xs">ID del trabajo: {job.id}</CardDescription>
              </div>
              <div className="flex items-center gap-2">
                {getStatusIcon(job.status)}
                {getStatusBadge(job.status)}
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4 pt-6">
            {(job.status === "processing" || job.status === "queued") && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="font-mono text-muted-foreground">Progreso</span>
                  <span className="font-mono font-semibold text-foreground">{job.progress}%</span>
                </div>
                <Progress value={job.progress} className="h-3" />
              </div>
            )}

            {job.status === "completed" && job.result && (
              <div className="space-y-4">
                <div className="grid gap-4 rounded-lg border-2 border-primary bg-muted p-4 sm:grid-cols-2">
                  <div>
                    <p className="font-mono text-sm uppercase text-muted-foreground">Hablantes Detectados</p>
                    <p className="font-mono text-2xl font-bold text-foreground">{job.result.speakers_detected}</p>
                  </div>
                  <div>
                    <p className="font-mono text-sm uppercase text-muted-foreground">Tiempo de Procesamiento</p>
                    <p className="font-mono text-2xl font-bold text-foreground">
                      {job.result.processing_time.toFixed(1)}s
                    </p>
                  </div>
                </div>

                <div className="space-y-2">
                  <p className="font-mono text-sm font-semibold uppercase text-foreground">Descargar Hablantes:</p>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {Array.from({ length: job.result.speakers_detected }).map((_, idx) => (
                      <Button
                        key={idx}
                        onClick={() => downloadSpeaker(job.id, idx, job.filename)}
                        className="bg-black text-white font-mono uppercase hover:bg-black/80"
                      >
                        <Download className="mr-2 h-4 w-4" />
                        Hablante {idx + 1}
                      </Button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {job.status === "failed" && job.error && (
              <div className="rounded-lg border-2 border-destructive bg-destructive/10 p-4">
                <p className="font-mono text-sm text-destructive">{job.error}</p>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
