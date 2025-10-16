import numpy as np
import cv2

# Magic lasso is currently not very magic and more just bad, plan to improve it.
# Tried to snap to edges using Canny, but it's bad.

# Global variables for mouse interaction
drawing = False
ix, iy = -1, -1
ex, ey = -1, -1  # Track end for rectangular
points = []
img_copy = None

# Helper to create blank mask
def create_mask(height, width):
    return np.zeros((height, width), dtype=np.uint8)

# Mock process_image: Load from file
def process_image():
    img = cv2.imread('tests/test_image2.png')
    if img is None:
        # Fallback to synthetic if file not found
        height, width = 400, 400
        img = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.rectangle(img, (100, 100), (300, 300), (255, 0, 0), -1)  # Red square
        cv2.circle(img, (200, 200), 50, (0, 255, 0), -1)  # Green circle
        for i in range(height):
            img[i, :] = i % 256
        cv2.imwrite('test_image.png', img)  # Save for next time
    return img

# Mouse callback for rectangular (click-drag)
def draw_rectangle(event, x, y, flags, param):
    global ix, iy, ex, ey, drawing, img_copy
    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix, iy = x, y
    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            temp = img_copy.copy()
            cv2.rectangle(temp, (ix, iy), (x, y), (0, 255, 0), 2)
            cv2.imshow('Image', temp)
    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        ex, ey = x, y  # Capture end point
        cv2.rectangle(img_copy, (ix, iy), (ex, ey), (0, 255, 0), 2)
        cv2.imshow('Image', img_copy)

# Mouse callback for polygonal (click for vertices)
def draw_polygonal(event, x, y, flags, param):
    global points, img_copy
    if event == cv2.EVENT_LBUTTONDOWN:
        points.append([x, y])
        cv2.circle(img_copy, (x, y), 3, (0, 255, 0), -1)
        if len(points) > 1:
            cv2.line(img_copy, tuple(points[-2]), tuple(points[-1]), (0, 255, 0), 2)
        cv2.imshow('Image', img_copy)

# Mouse callback for freeform/magic (drag to draw continuous path)
def draw_freeform(event, x, y, flags, param):
    global points, drawing, img_copy
    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        points = [[x, y]]  # Start new path
    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            points.append([x, y])
            cv2.line(img_copy, tuple(points[-2]), tuple(points[-1]), (0, 255, 0), 1)
            cv2.imshow('Image', img_copy)
    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        points.append([x, y])  # End point

# Run selection and display results
def run_selection(img, title):
    global points, img_copy, ix, iy, ex, ey, drawing
    img_copy = img.copy()
    cv2.namedWindow('Image')
    points = []
    ix, iy, ex, ey = -1, -1, -1, -1
    drawing = False

    if title == 'Rectangular':
        cv2.setMouseCallback('Image', draw_rectangle)
    elif title == 'Polygonal':
        cv2.setMouseCallback('Image', draw_polygonal)
    elif title in ['Freeform', 'Magic Lasso']:
        cv2.setMouseCallback('Image', draw_freeform)

    cv2.imshow('Image', img_copy)
    print(f"Instructions for {title}:")
    if title == 'Rectangular':
        print("Click and drag to draw rectangle. Press 's' to save, 'r' to reset, 'q' to quit.")
    elif title == 'Polygonal':
        print("Click to add vertices (straight lines). Press 's' to close and save, 'r' to reset, 'q' to quit.")
    else:
        print("Hold click and drag to draw path. Release mouse, then press 's' to close and save, 'r' to reset, 'q' to quit.")

    while True:
        key = cv2.waitKey(1) & 0xFF
        if key == ord('s') and (len(points) >= 3 or (title == 'Rectangular' and ex != -1)):
            height, width = img.shape[:2]
            mask = create_mask(height, width)
            if title == 'Rectangular':
                x1, y1 = min(ix, ex), min(iy, ey)
                x2, y2 = max(ix, ex), max(iy, ey)
                if x1 < x2 and y1 < y2:  # Ensure valid rect
                    cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)
            elif title == 'Polygonal' or title == 'Freeform':
                path = np.array(points, np.int32)
                cv2.fillPoly(mask, [path], 255)
            elif title == 'Magic Lasso':
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                edges = cv2.Canny(gray, 100, 150)
                path = []
                seed_points = points + [points[0]]  # Close loop
                for i in range(len(seed_points) - 1):
                    start, end = seed_points[i], seed_points[i+1]
                    start_arr, end_arr = np.array(start), np.array(end)
                    distance = np.linalg.norm(end_arr - start_arr)
                    num_steps = int(distance / 5) + 1 if distance > 0 else 1
                    line_path = np.linspace(start_arr, end_arr, num=num_steps, dtype=int)
                    for pt in line_path:
                        snapped = False
                        for r in range(1, 50):  # Larger radius
                            circle = np.zeros_like(edges)
                            cv2.circle(circle, tuple(pt), r, 255, 1)
                            intersects = cv2.bitwise_and(edges, circle)
                            if np.any(intersects):
                                max_val = np.max(intersects)
                                snap_pt_idx = np.argwhere(intersects == max_val)[0]
                                snap_pt = snap_pt_idx[::-1]  # (y,x) to (x,y)
                                path.append(snap_pt.tolist())  # As list
                                snapped = True
                                break
                        if not snapped:
                            path.append(pt.tolist())
                path = np.array(path, np.int32)
                if len(path) >= 3:
                    cv2.fillPoly(mask, [path], 255)

            # Display mask (white on black)
            visible_mask = np.where(mask > 0, 255, 0).astype(np.uint8)
            cv2.imshow('Mask', visible_mask)
            selected = cv2.bitwise_and(img, img, mask=mask)
            cv2.imshow('Selected Area', selected)
            print(f"{title} selection complete. Press any key in windows to continue.")
            cv2.waitKey(0)
            break
        elif key == ord('r'):
            points = []
            ix, iy, ex, ey = -1, -1, -1, -1
            img_copy = img.copy()
            cv2.imshow('Image', img_copy)
        elif key == ord('q'):
            break

    cv2.destroyAllWindows()

# Main interactive menu
if __name__ == "__main__":
    img = process_image()
    print("Loaded test_image.png (or created synthetic if not found).")

    while True:
        print("\nSelect a tool (or 'q' to quit):")
        print("1: Rectangular")
        print("2: Freeform")
        print("3: Polygonal")
        print("4: Magic Lasso")
        choice = input("Enter number: ").strip()
        if choice.lower() == 'q':
            break
        elif choice == '1':
            run_selection(img, 'Rectangular')
        elif choice == '2':
            run_selection(img, 'Freeform')
        elif choice == '3':
            run_selection(img, 'Polygonal')
        elif choice == '4':
            run_selection(img, 'Magic Lasso')
        else:
            print("Invalid choice.")