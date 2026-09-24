# Console design reference and visual QA

The native Godot console uses the **actual shadcn MCP server**, shadcn 4.21.0,
through the official MCP SDK's stdio client. No React runtime was added.

Evidence: `shadcn-mcp-tools.json` records the server's actual `tools/list`;
`shadcn-mcp-reference.json` records `view_items_in_registries` for Sidebar,
Resizable, Card, Tabs, Badge, Scroll Area, Chart and Tooltip;
`shadcn-mcp-examples.json` records `get_item_examples_from_registries` for
`card-demo`, including its complete CardHeader / CardTitle / CardDescription /
CardAction / CardContent / CardFooter example.

The registry-details call returned metadata rather than component source, so the
separate example call was used to inspect actual composition. The design borrows
quiet neutral surfaces, one restrained accent, persistent controls sidebar,
card title/action/content hierarchy, tabs for secondary circuits, visible status
badges and scrollable dense regions. It recreates these patterns with native
Godot Controls and a Theme. Resizable was investigated; fixed readable sidebars
and an expanding world viewport were chosen for predictable 4K use. No claim
that native Godot runs shadcn components is made.

The 3840×2160 layout uses the actual pixel canvas, not a 1080p scene scaled 2×.
The majority world SubViewport expands independently; sidebars carry controls and
selected circuit readouts; bottom cards show physiology, timing and a causal log.
Text updates cap at 10 Hz. Sparkline buffers hold 120 **neural** samples, only
update on new completed packets, and are cleared on reset. No per-neuron widget
or full-brain stream exists. Numeric labels use a monospace system font.

Runtime screenshots are saved by Godot after a rendered frame. They are actual
full-network experiments, not mocks: `final-v2/*/ecology.png` at world 1 s and
`final-v2/*/arena.png` at completion. `console_health` records actual window mode,
window dimensions, world viewport, FPS, refresh cost and renderer/physics health.
The user-desktop Godot window was also activated and inspected with computer-use.
The initial occluded screenshot showed the app behind it and is not used as proof;
only actual Godot captures are evidence.

Check the final visual QA record for fullscreen round-trip, controls, reset and
camera interaction. No old body-only screenshot is presented as the final UI.

