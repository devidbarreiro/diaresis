export const runtime = "nodejs"
export const dynamic = "force-dynamic"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://51.91.166.216:5000"

export async function GET(request: Request, { params }: { params: { jobId: string } }) {
  try {
    const jobId = params.jobId
    console.log("[v0] Proxy: Obteniendo estado del trabajo:", jobId)

    const response = await fetch(`${API_URL}/job/${jobId}`, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    })

    console.log("[v0] Proxy: Status:", response.status)
    console.log("[v0] Proxy: Content-Type:", response.headers.get("content-type"))

    const text = await response.text()
    console.log("[v0] Proxy: Respuesta como texto:", text)

    if (!response.ok) {
      console.log("[v0] Proxy: Error response:", text)
      return Response.json({ error: text }, { status: response.status })
    }

    try {
      const data = JSON.parse(text)
      console.log("[v0] Proxy: Estado del trabajo:", data)
      return Response.json(data)
    } catch (parseError) {
      console.error("[v0] Proxy: Error al parsear JSON:", parseError)
      console.log("[v0] Proxy: Texto recibido:", text)
      return Response.json({ error: `Respuesta no es JSON válido: ${text}` }, { status: 500 })
    }
  } catch (error) {
    console.error("[v0] Proxy: Error al obtener estado:", error)
    return Response.json({ error: error instanceof Error ? error.message : "Error desconocido" }, { status: 500 })
  }
}
