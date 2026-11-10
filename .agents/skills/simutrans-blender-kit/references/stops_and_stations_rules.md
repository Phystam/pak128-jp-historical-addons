# Simutrans Stop, Station & Platform Modeling Rules (OTRP & Standard)

Comprehensive geometric specifications, layout bitmask definitions, and modeling rules for creating stops, stations, and platforms (`obj=building`, `type=stop` or `type=generic_stop` or `type=harbour`) across straight ways, OTRP diagonal ways, and sloped terrain.

---

## 1. Stop Types & Hierarchy (Single, End, Intermediate)

In Simutrans, when players build platforms or stops along a road, track, or waterway, multiple adjacent tiles automatically join together to form a continuous station. The game assigns different layout images based on how each tile is connected to its neighbors:

1. **Single-Tile Station (単体・独立タイル / Isolated)**:
   - Placed as a 1-tile station or where no neighboring stop tile exists.
   - **Geometry**: The platform/pier/shelter sits centered on the tile. Both ends are cleanly finished with border posts, railings, steps, or end-plates. Does not extend all the way to the tile edge.

2. **End-Tile Station (端点タイル / Terminus / Edge Tile of a Station)**:
   - Forms the outer end of a multi-tile station (connected to a neighbor on one side, open to the outside on the other).
   - **Geometry**:
     - **Open Side**: Cleanly finished and aligned (same boundary as the single-tile stop).
     - **Connected Side**: **Must extend all the way to the tile boundary** ($X = \pm 1.0$ or $Y = \pm 1.0$ in Blender units). When adjacent tiles meet, there must be **zero gap** between the boardwalks/platforms.

3. **Intermediate-Tile Station (中間・通過タイル / Through / Combined Tile)**:
   - Sits in the middle of a continuous station, flanked by other stop tiles on both sides.
   - **Geometry**: **Both ends extend all the way to the opposite tile boundaries** (full length from $-1.0$ to $+1.0$ in Blender units). The platform floor, boardwalk, and railings seamlessly bridge across the tile boundary line.

---

## 2. Straight Ways (NS / EW) Geometry (Layouts 0..15)

In Blender coordinates ($+X = \text{East}$, $+Y = \text{North}$, $-Y = \text{South}$, $-X = \text{West}$, 1 tile = $2.0 \times 2.0$ units):
- **North-South (NS) Way**: Runs along the $Y$ axis ($X = 0$, $Y \in [-1.0, +1.0]$).
  - Platform sits on the West or East side of the way (e.g. $X \in [-0.7, -0.2]$ or $[0.2, 0.7]$).
  - **Single Tile**: Length $Y \in [-0.65, +0.65]$.
  - **End Tile (Near/North connected)**: Length $Y \in [-0.65, +1.00]$.
  - **End Tile (Far/South connected)**: Length $Y \in [-1.00, +0.65]$.
  - **Intermediate Tile**: Length $Y \in [-1.00, +1.00]$ (full tile).
- **East-West (EW) Way**: Runs along the $X$ axis ($Y = 0$, $X \in [-1.0, +1.0]$).
  - Platform sits on the North or South side of the way.
  - Length along $X$ follows the same single, end, and intermediate extensions as above.

### Bitmask Structure for Straight Stops:
- `(layout & 1)`: $0 = \text{NS}$, $1 = \text{EW}$.
- `(layout & 6)`: Corner connection bits:
  - `6` (`0b110`): Isolated / Single tile.
  - `4` (`0b100`): Connected at South/East (`dir_far`), open at North/West.
  - `2` (`0b010`): Connected at North/West (`dir_near`), open at South/East.
  - `0` (`0b000`): Connected at both ends (Intermediate / Combined).
- `(layout & 8)`: Facing bank / side ($0 = \text{front}$, $8 = \text{back}$).

---

## 3. OTRP Diagonal Ways Geometry (Layouts 16..47)

OTRP allows roads, canals, and tracks to run along $45^\circ$ diagonal lines across the tile grid. Reusing straight stop images on diagonal ways causes them to stick out at an incorrect $45^\circ$ angle. Dedicated diagonal models are required.

### 3.1 Triangular Drawing Region (`三角形の描画範囲` — Not Tile Center!)
A diagonal way in Simutrans **never passes through the tile center $(0, 0)$**. Because a diagonal way connects the midpoints of two adjacent edges of a tile (e.g. North $(0, +1)$ and East $(+1, 0)$ for `ne`), its drawing region occupies a **triangular half of the tile** bounded by the tile center diagonal ($X \pm Y = 0$) and the two outer edges meeting at the corner vertex:
- **Vertical Diagonal** (`layout & 0x30 == 0x10`, layouts `16..31`, projecting vertically on screen at camera `az = 45.0`):
  - **`bit 0 == 0` (`ne` tile, ribi = North + East = 5)**: Occupies the **Right Triangle** $0 \le X + Y \le 2$, with way centerline at **$X + Y = +1.0$** connecting $(0, +1)$ and $(+1, 0)$.
  - **`bit 0 == 1` (`sw` tile, ribi = South + West = 10)**: Occupies the **Left Triangle** $-2 \le X + Y \le 0$, with way centerline at **$X + Y = -1.0$** connecting $(-1, 0)$ and $(0, -1)$.
- **Horizontal Diagonal** (`layout & 0x30 == 0x20`, layouts `32..47`, projecting horizontally on screen):
  - **`bit 0 == 0` (`se` tile, ribi = South + East = 6)**: Occupies the **Bottom Triangle** $0 \le X - Y \le 2$, with way centerline at **$X - Y = +1.0$** connecting $(+1, 0)$ and $(0, -1)$.
  - **`bit 0 == 1` (`nw` tile, ribi = North + West = 9)**: Occupies the **Top Triangle** $-2 \le X - Y \le 0$, with way centerline at **$X - Y = -1.0$** connecting $(0, +1)$ and $(-1, 0)$.

### 3.2 Alternating Triangle Placement (`タイル中心軸の三角形の辺側` vs `タイル四隅の三角形の頂点側 / 小三角エリア`)
When a diagonal way extends across multiple tiles, the tiles alternate `ne` $\to$ `sw` $\to$ `ne` $\to$ `sw` (or `se` $\to$ `nw` $\to$ `se` $\to$ `nw`). Notice that when an `ne` tile at $(0, 0)$ (centerline $X+Y = +1.0$) is followed by an `sw` tile at grid East $(+2, 0)$ (local centerline $X+Y = -1.0$, which in world coordinates is $(X+2)+Y = +1.0$), the two way segments are **perfectly collinear**!

In OTRP (`hausbauer.cc :: calc_diagonal_station_layout`), connected diagonal stop tiles inherit the **same** `front_back_bit` (`bit 3 = layout & 8`), while `bit 0` (`layout & 1`) alternates `0, 1, 0, 1` from tile to tile. Therefore, to form a **single continuous straight station line** along one bank of the diagonal way, the stop model **must alternate between the tile corner-vertex side (`小三角エリア`) and the tile center-axis side (`三角形の辺側`)** according to `bit 0` and `bit 3`:

- **For Vertical Diagonal (`16..31`)**:
  - **Right Bank (`front`, `bit 3 == 0`, layouts `16..23`)**:
    - **`bit 0 == 0` (`ne` tile, layouts `16, 18, 20, 22`)**: Placed in the **Corner Small Triangle (`タイル四隅の三角形の頂点側 / 小三角エリア`)** around **$X + Y = +1.50$** (between the `ne` canal at $X+Y = +1.0$ and the corner $(+1, +1)$ at $X+Y = +2.0$).
      - Tile boundaries along $X + Y = c$: UP edge ($Y = +1$) is at $Y - X = 2 - c$; DOWN edge ($X = +1$) is at $Y - X = -(2 - c)$.
    - **`bit 0 == 1` (`sw` tile, layouts `17, 19, 21, 23`)**: Placed on the **Tile Center-Axis Side (`タイル中心軸の三角形の辺側`)** around **$X + Y = -0.50$** (between the `sw` canal at $X+Y = -1.0$ and the tile center diagonal $X+Y = 0$).
      - Tile boundaries along $X + Y = c'$: UP edge ($X = -1$) is at $Y - X = c' + 2$; DOWN edge ($Y = -1$) is at $Y - X = -(c' + 2)$.
    - At the shared tile edge between `ne` ($X = +1, Y = c - 1$) and `sw` ($X = -1, Y = c' + 1 = c - 1$), both platforms meet at the **exact same world coordinates with zero lateral offset and zero gap**!
  - **Left Bank (`back`, `bit 3 == 8`, layouts `24..31`)**:
    - Obtained by rotating the Right Bank models by $180^\circ$ around $Z$ (`turns = 2` in `rotate_layout`):
    - **`bit 0 == 0` (`ne` tile, layouts `24, 26, 28, 30`)**: Placed on the **Tile Center-Axis Side (`三角形の辺側`)** around **$X + Y = +0.50$**.
    - **`bit 0 == 1` (`sw` tile, layouts `25, 27, 29, 31`)**: Placed in the **Corner Small Triangle (`小三角エリア`)** around **$X + Y = -1.50$**.
- **For Horizontal Diagonal (`32..47`)**:
  - Generated automatically from `16..31` by $90^\circ$ / $270^\circ$ Z-rotations (`turns = 1, 3` of `gebaeude.cc :: rotate_layout`), placing platforms at $X - Y = \pm 1.50$ (`小三角エリア`) and $X - Y = \pm 0.50$ (`三角形の辺側`).

### 3.3 45-Degree Rotation, $1/\sqrt{2}$ Width Scaling & Boundary Miter:
- **Angle**: The model is rotated $45^\circ$ in Blender to align with the diagonal axes ($X + Y = \text{const}$ or $X - Y = \text{const}$).
- **Width**: A strip of coordinate sum width $\Delta(X+Y) = w$ has perpendicular 3D width $w / \sqrt{2}$, preserving consistent visual width on screen.
- **Single Tile (`conn_bits == 6`)**: Both ends are trimmed perpendicular to the diagonal line (`Y - X = const`) and aligned neatly.
- **End Tile (`conn_bits == 2` or `4`)**: The open end is trimmed square (`Y - X = const`), while the connected end extends to the tile boundary ($X = \pm 1$ or $Y = \pm 1$), naturally making the longer edge and shorter edge different lengths so they meet the neighbor tile edge flush.
- **Intermediate Tile (`conn_bits == 0`)**: Both ends extend all the way to the tile boundary lines ($X = \pm 1, Y = \pm 1$).

### 3.4 Exact 28 Rotation Orbits Across All 112 Layouts (`gebaeude.cc :: rotate_layout`)
Instead of approximating rotations, always generate all 112 layouts from the 28 canonical base models (`turns = 0, 1, 2, 3`, rotating by $-90^\circ \times \text{turn}$ around $Z$ in Blender):
- **Straight (`0..15`)**: `0: [0, 1, 8, 9]`, `2: [2, 5, 12, 11]`, `4: [4, 3, 10, 13]`, `6: [6, 7, 14, 15]`
- **Diagonal (`16..47`)**:
  - `16: [16, 40, 25, 33]`, `17: [17, 41, 24, 32]`
  - `18: [18, 44, 29, 35]`, `19: [19, 45, 28, 34]`
  - `20: [20, 42, 27, 37]`, `21: [21, 43, 26, 36]`
  - `22: [22, 46, 31, 39]`, `23: [23, 47, 30, 38]`
- **Single Slopes (`48..79`)**:
  - North-up base (`48, 50, 52, 54`): `[48, 65, 72, 57]`, `[50, 69, 76, 59]`, `[52, 67, 74, 61]`, `[54, 71, 78, 63]`
  - South-up base (`64, 66, 68, 70`): `[64, 49, 56, 73]`, `[66, 53, 60, 75]`, `[68, 51, 58, 77]`, `[70, 55, 62, 79]`
- **Double Slopes (`80..111`)**:
  - North-up base (`80, 82, 84, 86`): `[80, 97, 104, 89]`, `[82, 101, 108, 91]`, `[84, 99, 106, 93]`, `[86, 103, 110, 95]`
  - South-up base (`96, 98, 100, 102`): `[96, 81, 88, 105]`, `[98, 85, 92, 107]`, `[100, 83, 90, 109]`, `[102, 87, 94, 111]`

---

## 4. OTRP Slope Tile Stations (Layouts 48..111)

OTRP supports placing stops on sloped terrain (hills and ramps). Slopes run along the standard grid axes (North, South, East, West).

### Slope Indexing Offsets:
Slope station layouts reuse the straight station layout structure (0..15) with an additive index offset:
- **西・北向き緩坂 (Single slope North / West)**: Layout index $+48$ (Layouts 48..63)
  - In Simutrans (`slope_t::north`), "North slope" means the slope descends towards North (South side is RAISED / UP, North side is LOWERED / DOWN).
  - In `pak128`, $+Z$ increases towards $-Y$ (South) in the base NS model.
- **東・南向き緩坂 (Single slope South / East)**: Layout index $+64$ (Layouts 64..79)
  - In Simutrans (`slope_t::south`), "South slope" means the slope descends towards South (North side is RAISED / UP, South side is LOWERED / DOWN).
  - In `pak128`, $+Z$ increases towards $+Y$ (North) in the base NS model.
- **西・北向き急坂 (Double slope North / West)**: Layout index $+80$ (Layouts 80..95)
  - Double height: South side is raised by $\Delta Z = 0.8165\text{ m}$.
- **東・南向き急坂 (Double slope South / East)**: Layout index $+96$ (Layouts 96..111)
  - Double height: North side is raised by $\Delta Z = 0.8165\text{ m}$.

### `dims` Parameter in `.dat`:
- **`dims=1,1,48`**: Flat straight (0..15) + OTRP diagonal (16..47). Use for waterways where terrain cannot slope.
- **`dims=1,1,80`**: Flat straight (0..15) + OTRP diagonal (16..47) + Single slopes (48..79).
- **`dims=1,1,112`**: Flat straight (0..15) + OTRP diagonal (16..47) + Single slopes (48..79) + Double slopes (80..111). Standard for road and rail stops in `pak128` (where `height_conversion_factor=2` makes double slopes the primary hill type).

### Slope Geometry in Blender:
In `pak128` (`tile_world = 2.0`, `height_step = 8`):
- Single-slope height difference: $\Delta Z = 0.4082\text{ m}$ (in Blender units) over $\Delta = 2.0\text{ m}$.
- Double-slope height difference: $\Delta Z = 0.8165\text{ m}$ (in Blender units) over $\Delta = 2.0\text{ m}$.
- The platform floor and railings slope uniformly along the incline ($\tan \theta = \frac{\Delta Z}{2.0}$).

---

## 5. Summary Matrix of Layouts (112 Total)

| Layout Range | Category | Axis / Direction | Sub-variants |
| :--- | :--- | :--- | :--- |
| `0 .. 15` | Flat Straight | NS ($Y$) / EW ($X$) | Single, End (Near), End (Far), Intermediate $\times$ Front/Back |
| `16 .. 31` | Flat Diagonal (Vertical) | NW $\leftrightarrow$ SE | Single, End (Up/Left), End (Down/Right), Intermediate $\times$ Front/Back $\times$ East/West |
| `32 .. 47` | Flat Diagonal (Horizontal) | SW $\leftrightarrow$ NE | Single, End (Up/Left), End (Down/Right), Intermediate $\times$ Front/Back $\times$ East/West |
| `48 .. 63` | Single Slope NW | Up toward North / West | Base layouts 0..15 tilted along single slope |
| `64 .. 79` | Single Slope SE | Up toward South / East | Base layouts 0..15 tilted along single slope |
| `80 .. 95` | Double Slope NW | Up toward North / West | Base layouts 0..15 tilted along double slope |
| `96 .. 111` | Double Slope SE | Up toward South / East | Base layouts 0..15 tilted along double slope |
