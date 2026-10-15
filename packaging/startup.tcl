# Keep this UI in the bootloader so it also covers one-file extraction.
.root.canvas delete all
wm attributes . -transparentcolor {}
set startup_scale [expr {[winfo fpixels . 1i] / 96.0}]
.root.canvas configure -width 620 -height 380 -background #10141e
wm geometry . 620x380+[expr {([winfo screenwidth .]-620)/2}]+[expr {([winfo screenheight .]-380)/2}]
wm title . {Twitch Spy is starting}
.root.canvas create text 32 30 -anchor nw -fill #a78bfa -font {{Segoe UI} 11 bold} -text {TWITCH SPY}
.root.canvas create text 32 66 -anchor nw -fill #f2f4fa -font {{Segoe UI} 24 bold} -text {Getting things ready}
.root.canvas create text 32 114 -anchor nw -fill #aab4c8 -font {{Segoe UI} 11} -text {Your browser will open automatically. You can keep working.}
.root.canvas create rectangle 32 153 588 156 -fill #283246 -outline {}
.root.canvas create rectangle 32 153 120 156 -fill #a78bfa -outline {} -tag pulse
.root.canvas create text 32 178 -anchor nw -fill #7e91b0 -font {Consolas 9} -tag history
.root.canvas create text 32 345 -anchor nw -fill #aab4c8 -font {{Segoe UI} 10} -tag elapsed
set startup_lines {}
set startup_epoch [clock seconds]
set pulse_position 32
proc canvas_text_update {canvas tag _var - -} {
    upvar $_var value
    global startup_lines startup_epoch
    set clean [string range [string map [list "\n" " " "\r" " "] $value] 0 78]
    # clock format needs Tcl library files absent from the minimal bootloader.
    lappend startup_lines "[format {%3ds} [expr {[clock seconds]-$startup_epoch}]]  $clean"
    set startup_lines [lrange $startup_lines end-7 end]
}
proc startup_tick {} {
    global startup_lines startup_epoch pulse_position startup_scale
    .root.canvas itemconfigure history -text [join $startup_lines "\n"]
    .root.canvas itemconfigure elapsed -text "Starting up · [expr {[clock seconds]-$startup_epoch}]s elapsed"
    set pulse_position [expr {32 + ($pulse_position - 32 + 6) % 468}]
    .root.canvas coords pulse [expr {$pulse_position*$startup_scale}] [expr {153*$startup_scale}] [expr {($pulse_position+88)*$startup_scale}] [expr {156*$startup_scale}]
    after 80 startup_tick
}
.root.canvas scale all 0 0 $startup_scale $startup_scale
foreach item [.root.canvas find withtag all] {
    if {[.root.canvas type $item] eq "text"} {
        set font [.root.canvas itemcget $item -font]
        set pixels [expr {-round([lindex $font 1] * 96.0 / 72.0 * $startup_scale)}]
        .root.canvas itemconfigure $item -font [lreplace $font 1 1 $pixels]
    }
}
set width [expr {round(620*$startup_scale)}]
set height [expr {round(380*$startup_scale)}]
.root.canvas configure -width $width -height $height
wm geometry . ${width}x${height}+[expr {([winfo screenwidth .]-$width)/2}]+[expr {([winfo screenheight .]-$height)/2}]
set status_text {Preparing bundled components...}
startup_tick
