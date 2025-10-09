export const runtime = "nodejs"
export const dynamic = "force-dynamic"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://51.91.166.216:5000"

export async function GET(request: Request, { params }: { params: { jobId: string; speakerId: string } }) {
  try {
    const { jobId, speakerId } = params
    console.log("[v0] Proxy: Descargando speaker:", speakerId, "del job:", jobId)

    const response = await fetch(`${API_URL}/job/${jobId}/download/${speakerId}`, {
      method: "GET",
    })

    console.log("[v0] Proxy: Status:", response.status)

    if (!response.ok) {
      const text = await response.text()
      console.log("[v0] Proxy: Error response:", text)
      return new Response(text, { status: response.status })
    }

    const blob = await response.blob()
    console.log("[v0] Proxy: Archivo descargado, tamaño:", blob.size)

    return new Response(blob, {
      headers: {
        "Content-Type": "audio/wav",
        "Content-Disposition": `attachment; filename="speaker_${speakerId}.wav"`,
      },
    })
  } catch (error) {
    console.error("[v0] Proxy: Error al descargar:", error)
    return new Response(JSON.stringify({ error: error instanceof Error ? error.message : "Error desconocido" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    })
  }
}
