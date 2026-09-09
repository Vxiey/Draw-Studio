from pathlib import Path

# The first focused run exposed a real planner issue: tiny high-contrast details
# could disappear after the smoothed NMS pass. Add a raw strong-edge safety pass
# before connected-component filtering; isolated single-pixel noise still gets
# removed by the component gate that follows.
p=Path('Sketch2Planner.py')
text=p.read_text(encoding='utf-8')
old="""    mask=thin>=threshold
    mask[[0,-1],:]=False;mask[:,[0,-1]]=False
    mask,removed,protected=_filter_components(mask,thin,threshold,
        min_component=int(cfg['min_component']),protect_factor=float(cfg['protect_factor']),cancelled=cancelled)
"""
new="""    mask=thin>=threshold
    # Micro-detail protection uses the unblurred source only for very strong
    # local boundaries. This recovers tiny eyes/symbols/corners that Gaussian
    # smoothing can erase, without turning ordinary low-contrast texture into
    # sketch noise.
    raw=np.asarray(flat,dtype=np.float32)
    raw_lum=raw[:,:,0]*.2126+raw[:,:,1]*.7152+raw[:,:,2]*.0722
    rgx=np.zeros_like(raw_lum);rgy=np.zeros_like(raw_lum)
    rgx[:,1:-1]=raw_lum[:,2:]-raw_lum[:,:-2];rgy[1:-1,:]=raw_lum[2:,:]-raw_lum[:-2,:]
    rcx=np.zeros_like(raw);rcy=np.zeros_like(raw)
    rcx[:,1:-1,:]=raw[:,2:,:]-raw[:,:-2,:];rcy[1:-1,:,:]=raw[2:,:,:]-raw[:-2,:,:]
    raw_strength=np.hypot(rgx,rgy)*.72 + np.sqrt(np.max(rcx*rcx+rcy*rcy,axis=2))*.40
    micro_threshold=max(88.0,threshold*1.18)
    micro=raw_strength>=micro_threshold
    micro[[0,-1],:]=False;micro[:,[0,-1]]=False
    mask|=micro
    strength=np.maximum(thin,raw_strength)
    mask,removed,protected=_filter_components(mask,strength,threshold,
        min_component=int(cfg['min_component']),protect_factor=float(cfg['protect_factor']),cancelled=cancelled)
"""
if text.count(old)!=1:raise SystemExit('Sketch2 micro-protection anchor missing')
p.write_text(text.replace(old,new,1),encoding='utf-8')

# Correct the test to inspect the local contour around the feature rather than
# demanding that the filled centre itself be an edge pixel.
p=Path('test_sketch2_v10131.py')
text=p.read_text(encoding='utf-8')
old="""        out,meta=contour_image_v2(im,detail='Detailed')
        self.assertLess(out.convert('L').getpixel((36,29)),255)
        self.assertGreater(meta['ink_pixels'],20)
"""
new="""        out,meta=contour_image_v2(im,detail='Detailed')
        gray=out.convert('L')
        local=[gray.getpixel((x,y)) for y in range(25,34) for x in range(32,41)]
        self.assertIn(0,local)
        self.assertGreater(meta['ink_pixels'],20)
"""
if text.count(old)!=1:raise SystemExit('Sketch2 tiny-feature test anchor missing')
p.write_text(text.replace(old,new,1),encoding='utf-8')

# v1.0.131 is a beta after the RC2 field test. Keep release-hardening tests
# strict, but update only stale fixtures/expectations to the new channel/version.
p=Path('test_release_v100.py')
text=p.read_text(encoding='utf-8')
old="self.assertEqual(BUILD_CHANNEL,'rc')"
if text.count(old)!=1:raise SystemExit('test_release_v100 BUILD_CHANNEL anchor missing')
p.write_text(text.replace(old,"self.assertEqual(BUILD_CHANNEL,'beta')",1),encoding='utf-8')

p=Path('test_step30_release_candidate_hardening_v10129rc1.py')
text=p.read_text(encoding='utf-8')
old='"filevers=(1,0,129,0)\\nprodvers=(1,0,129,0)\\n"'
new='"filevers=(1,0,131,0)\\nprodvers=(1,0,131,0)\\n"'
if text.count(old)!=1:raise SystemExit('release hardening version_info fixture anchor missing')
text=text.replace(old,new,1)
# Change only the literal release-manifest fixture channel. The intentional
# channel='rc' mismatch test remains untouched.
old='"channel":"rc",\n                    "files"'
new='"channel":"beta",\n                    "files"'
if text.count(old)!=1:raise SystemExit('release hardening manifest channel fixture anchor missing')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')

print('SKETCH2_MICRO_DETAIL_AND_METADATA_FIX=APPLIED')
