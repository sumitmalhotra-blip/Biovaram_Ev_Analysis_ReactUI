"use client"

import { useState } from "react"
import { 
  Image as ImageIcon, 
  Download, 
  Trash2, 
  X, 
  Maximize2, 
  Calendar, 
  Info,
  RotateCcw,
  Grid,
  List,
  Search
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { useAnalysisStore, type SavedImage } from "@/lib/store"
import { useToast } from "@/hooks/use-toast"
import { cn } from "@/lib/utils"

interface SavedImagesGalleryProps {
  className?: string
  maxHeight?: string
  showHeader?: boolean
}

// Chart type to color mapping
const chartTypeColors: Record<string, string> = {
  histogram: "bg-blue-500",
  scatter: "bg-green-500",
  line: "bg-purple-500",
  bar: "bg-orange-500",
  heatmap: "bg-red-500",
  pie: "bg-pink-500",
}

// Source to badge variant mapping
const sourceVariants: Record<string, "default" | "secondary" | "outline"> = {
  "FCS Analysis": "default",
  "NTA Analysis": "secondary",
  "Cross-Compare": "outline",
}

export function SavedImagesGallery({ 
  className, 
  maxHeight = "500px",
  showHeader = true 
}: SavedImagesGalleryProps) {
  const { savedImages, removeImage, clearSavedImages } = useAnalysisStore()
  const { toast } = useToast()
  
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid")
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedImage, setSelectedImage] = useState<SavedImage | null>(null)
  const [showPreview, setShowPreview] = useState(false)

  // Filter images based on search
  const filteredImages = savedImages.filter((img) =>
    img.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    img.source.toLowerCase().includes(searchQuery.toLowerCase()) ||
    img.chartType.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleDownload = (image: SavedImage) => {
    const link = document.createElement("a")
    link.href = image.dataUrl
    link.download = `${image.title.replace(/\s+/g, "_")}_${new Date(image.timestamp).toISOString().slice(0, 10)}.${image.metadata?.format || "png"}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
    toast({
      title: "Image Downloaded",
      description: `${image.title} has been downloaded.`,
    })
  }

  const handleDelete = (imageId: string) => {
    removeImage(imageId)
    toast({
      title: "Image Removed",
      description: "The image has been removed from the gallery.",
    })
  }

  const handleClearAll = () => {
    clearSavedImages()
    toast({
      title: "Gallery Cleared",
      description: "All saved images have been removed.",
    })
  }

  const formatDate = (date: Date) => {
    return new Date(date).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })
  }

  if (savedImages.length === 0) {
    return (
      <Card className={cn("card-3d", className)}>
        {showHeader && (
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <ImageIcon className="h-5 w-5 text-primary" />
              Saved Images Gallery
            </CardTitle>
            <CardDescription>
              Save chart snapshots here for later reference
            </CardDescription>
          </CardHeader>
        )}
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="w-16 h-16 rounded-2xl bg-secondary/50 flex items-center justify-center mb-4">
              <ImageIcon className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="font-semibold text-lg mb-2">No Saved Images</h3>
            <p className="text-sm text-muted-foreground max-w-sm">
              Save chart snapshots from your analysis tabs to view them here. 
              Use the camera icon on charts to capture and save.
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={cn("card-3d", className)}>
      {showHeader && (
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <ImageIcon className="h-5 w-5 text-primary" />
                Saved Images Gallery
              </CardTitle>
              <CardDescription>
                {savedImages.length} image{savedImages.length !== 1 ? "s" : ""} saved
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => setViewMode(viewMode === "grid" ? "list" : "grid")}
                    >
                      {viewMode === "grid" ? (
                        <List className="h-4 w-4" />
                      ) : (
                        <Grid className="h-4 w-4" />
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    Switch to {viewMode === "grid" ? "list" : "grid"} view
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive">
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Clear All Images?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will permanently remove all {savedImages.length} saved images from the gallery.
                      This action cannot be undone.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction onClick={handleClearAll} className="bg-destructive text-destructive-foreground">
                      Clear All
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          </div>
        </CardHeader>
      )}
      
      <CardContent className="space-y-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search images..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Gallery */}
        <ScrollArea style={{ maxHeight }}>
          {viewMode === "grid" ? (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {filteredImages.map((image) => (
                <div
                  key={image.id}
                  className="group relative rounded-lg border border-border/50 overflow-hidden bg-secondary/20 hover:border-primary/50 transition-colors cursor-pointer"
                  onClick={() => {
                    setSelectedImage(image)
                    setShowPreview(true)
                  }}
                >
                  {/* Thumbnail */}
                  <div className="aspect-video relative overflow-hidden">
                    <img
                      src={image.thumbnailUrl || image.dataUrl}
                      alt={image.title}
                      className="w-full h-full object-cover transition-transform group-hover:scale-105"
                    />
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
                      <Maximize2 className="h-6 w-6 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                  </div>
                  
                  {/* Info */}
                  <div className="p-2">
                    <p className="text-sm font-medium truncate">{image.title}</p>
                    <div className="flex items-center gap-1 mt-1">
                      <Badge 
                        variant={sourceVariants[image.source] || "outline"} 
                        className="text-xs py-0"
                      >
                        {image.source}
                      </Badge>
                    </div>
                  </div>
                  
                  {/* Chart type indicator */}
                  <div 
                    className={cn(
                      "absolute top-2 right-2 w-3 h-3 rounded-full",
                      chartTypeColors[image.chartType] || "bg-gray-500"
                    )} 
                  />
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {filteredImages.map((image) => (
                <div
                  key={image.id}
                  className="flex items-center gap-3 p-3 rounded-lg border border-border/50 bg-secondary/20 hover:border-primary/50 transition-colors"
                >
                  {/* Thumbnail */}
                  <div 
                    className="w-16 h-12 rounded overflow-hidden shrink-0 cursor-pointer"
                    onClick={() => {
                      setSelectedImage(image)
                      setShowPreview(true)
                    }}
                  >
                    <img
                      src={image.thumbnailUrl || image.dataUrl}
                      alt={image.title}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  
                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm truncate">{image.title}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge 
                        variant={sourceVariants[image.source] || "outline"} 
                        className="text-xs py-0"
                      >
                        {image.source}
                      </Badge>
                      <span className="text-xs text-muted-foreground flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        {formatDate(image.timestamp)}
                      </span>
                    </div>
                  </div>
                  
                  {/* Actions */}
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDownload(image)
                      }}
                    >
                      <Download className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDelete(image.id)
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>

      {/* Preview Dialog */}
      <Dialog open={showPreview} onOpenChange={setShowPreview}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedImage?.title}
              <Badge variant={sourceVariants[selectedImage?.source || ""] || "outline"}>
                {selectedImage?.source}
              </Badge>
            </DialogTitle>
            <DialogDescription className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                {selectedImage && formatDate(selectedImage.timestamp)}
              </span>
              {selectedImage?.metadata?.width && selectedImage?.metadata?.height && (
                <span>
                  {selectedImage.metadata.width} × {selectedImage.metadata.height}
                </span>
              )}
              <span className="capitalize">{selectedImage?.chartType} chart</span>
            </DialogDescription>
          </DialogHeader>
          
          <div className="flex-1 overflow-auto">
            {selectedImage && (
              <img
                src={selectedImage.dataUrl}
                alt={selectedImage.title}
                className="w-full h-auto rounded-lg"
              />
            )}
          </div>
          
          <div className="flex items-center justify-between pt-4 border-t">
            {selectedImage?.metadata?.notes && (
              <p className="text-sm text-muted-foreground flex items-start gap-2">
                <Info className="h-4 w-4 shrink-0 mt-0.5" />
                {selectedImage.metadata.notes}
              </p>
            )}
            <div className="flex items-center gap-2 ml-auto">
              <Button
                variant="outline"
                size="sm"
                className="gap-2"
                onClick={() => selectedImage && handleDownload(selectedImage)}
              >
                <Download className="h-4 w-4" />
                Download
              </Button>
              <Button
                variant="destructive"
                size="sm"
                className="gap-2"
                onClick={() => {
                  if (selectedImage) {
                    handleDelete(selectedImage.id)
                    setShowPreview(false)
                  }
                }}
              >
                <Trash2 className="h-4 w-4" />
                Delete
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </Card>
  )
}

/**
 * Utility function to capture a chart element as an image
 * This can be used by chart components to save their content
 * Note: Requires html2canvas package to be installed: npm install html2canvas
 */
export async function captureChartAsImage(
  chartElement: HTMLElement,
  title: string,
  source: string,
  chartType: SavedImage['chartType'],
  options?: {
    format?: "png" | "jpeg"
    quality?: number
    notes?: string
  }
): Promise<SavedImage | null> {
  try {
    // Dynamic import of html2canvas - will fail gracefully if not installed
    let html2canvas: any
    try {
      html2canvas = (await import("html2canvas")).default
    } catch {
      console.warn("html2canvas not installed. Run: npm install html2canvas")
      // Fallback: try to use canvas API directly for SVG-based charts
      const svgElement = chartElement.querySelector("svg")
      if (svgElement) {
        return await captureSVGAsImage(svgElement, title, source, chartType, options)
      }
      return null
    }
    
    const canvas = await html2canvas(chartElement, {
      backgroundColor: null,
      scale: 2, // Higher quality
      logging: false,
    })
    
    const format = options?.format || "png"
    const quality = options?.quality || 0.9
    const dataUrl = canvas.toDataURL(`image/${format}`, quality)
    
    // Create thumbnail (smaller version)
    const thumbCanvas = document.createElement("canvas")
    const thumbWidth = 200
    const thumbHeight = (canvas.height / canvas.width) * thumbWidth
    thumbCanvas.width = thumbWidth
    thumbCanvas.height = thumbHeight
    const thumbCtx = thumbCanvas.getContext("2d")
    if (thumbCtx) {
      thumbCtx.drawImage(canvas, 0, 0, thumbWidth, thumbHeight)
    }
    const thumbnailUrl = thumbCanvas.toDataURL(`image/${format}`, 0.7)
    
    return {
      id: crypto.randomUUID(),
      title,
      source,
      chartType,
      dataUrl,
      thumbnailUrl,
      timestamp: new Date(),
      metadata: {
        width: canvas.width,
        height: canvas.height,
        format,
        notes: options?.notes,
      },
    }
  } catch (error) {
    console.error("Failed to capture chart:", error)
    return null
  }
}

/**
 * Fallback: Capture SVG element as an image
 */
async function captureSVGAsImage(
  svgElement: SVGElement,
  title: string,
  source: string,
  chartType: SavedImage['chartType'],
  options?: {
    format?: "png" | "jpeg"
    quality?: number
    notes?: string
  }
): Promise<SavedImage | null> {
  try {
    const svgData = new XMLSerializer().serializeToString(svgElement)
    const svgBlob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" })
    const url = URL.createObjectURL(svgBlob)
    
    return new Promise((resolve) => {
      const img = new Image()
      img.onload = () => {
        const canvas = document.createElement("canvas")
        canvas.width = img.width * 2
        canvas.height = img.height * 2
        const ctx = canvas.getContext("2d")
        if (ctx) {
          ctx.scale(2, 2)
          ctx.drawImage(img, 0, 0)
        }
        
        const format = options?.format || "png"
        const dataUrl = canvas.toDataURL(`image/${format}`, options?.quality || 0.9)
        
        // Create thumbnail
        const thumbCanvas = document.createElement("canvas")
        const thumbWidth = 200
        const thumbHeight = (canvas.height / canvas.width) * thumbWidth
        thumbCanvas.width = thumbWidth
        thumbCanvas.height = thumbHeight
        const thumbCtx = thumbCanvas.getContext("2d")
        if (thumbCtx) {
          thumbCtx.drawImage(canvas, 0, 0, thumbWidth, thumbHeight)
        }
        const thumbnailUrl = thumbCanvas.toDataURL(`image/${format}`, 0.7)
        
        URL.revokeObjectURL(url)
        
        resolve({
          id: crypto.randomUUID(),
          title,
          source,
          chartType,
          dataUrl,
          thumbnailUrl,
          timestamp: new Date(),
          metadata: {
            width: canvas.width,
            height: canvas.height,
            format,
            notes: options?.notes,
          },
        })
      }
      img.onerror = () => {
        URL.revokeObjectURL(url)
        resolve(null)
      }
      img.src = url
    })
  } catch (error) {
    console.error("Failed to capture SVG:", error)
    return null
  }
}
