"use client"

import { useState } from "react"
import { UploadSection } from "@/components/upload-section"
import { JobsList } from "@/components/jobs-list"
import { AudioWaveform as Waveform } from "lucide-react"

export default function Home() {
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  const handleUploadSuccess = () => {
    setRefreshTrigger((prev) => prev + 1)
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b-4 border-primary bg-card">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary">
              <Waveform className="h-6 w-6 text-primary-foreground" />
            </div>
            <div>
              <h1 className="font-mono text-2xl font-bold uppercase tracking-tight text-foreground">
                Separación de Voces
              </h1>
              <p className="text-sm text-muted-foreground">Separa el audio por hablante automáticamente</p>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto max-w-4xl px-4 py-8">
        <div className="space-y-8">
          <UploadSection onUploadSuccess={handleUploadSuccess} />
          <JobsList refreshTrigger={refreshTrigger} />
        </div>
      </main>
    </div>
  )
}
