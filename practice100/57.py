bottom_and_height = [[13, 40], [15, 30], [20, 25]]
for b_and_h in bottom_and_height:
    bottom = b_and_h[0]
    height = b_and_h[1]
    area = bottom * height / 2
    print(f"底辺{bottom}×高さ{height}=面積{int(area)}")
