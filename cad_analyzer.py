# cad_analyzer.py (Uppdaterad version)
import os

def analyze_3d_file(file_path):
    ext = file_path.split('.')[-1].lower()
    try:
        if ext in ['stl']:
            try:
                import trimesh
                mesh = trimesh.load(file_path)
                extents = mesh.extents
                return {
                    "success": True,
                    "length": float(extents[0]),
                    "width": float(extents[1]),
                    "thickness": float(extents[2]),
                    "volume_cm3": float(mesh.volume / 1000.0),
                    "source": "STL (Trimesh)"
                }
            except ImportError:
                return {"success": False, "error": "Biblioteket 'trimesh' saknas. Installera via pip install trimesh."}
            
        elif ext in ['step', 'stp', 'iges', 'igs']:
            try:
                from OCC.Core.STEPControl import STEPControl_Reader
                from OCC.Core.IGESControl import IGESControl_Reader
                from OCC.Core.GProp import GProp_GProps
                from OCC.Core.BRepGProp import brepgprop_VolumeProperties
                from OCC.Core.BRepBndLib import brepbndlib_Add
                from OCC.Core.Bnd import Bnd_Box
                
                if ext in ['step', 'stp']:
                    reader = STEPControl_Reader()
                else:
                    reader = IGESControl_Reader()
                    
                status = reader.ReadFile(file_path)
                if status == 1:
                    reader.TransferRoots()
                    shape = reader.Shape()
                    
                    bbox = Bnd_Box()
                    brepbndlib_Add(shape, bbox)
                    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
                    
                    length = abs(xmax - xmin)
                    width = abs(ymax - ymin)
                    thickness = abs(zmax - zmin)
                    
                    gprops = GProp_GProps()
                    brepgprop_VolumeProperties(shape, gprops)
                    volume_mm3 = gprops.Mass()
                    volume_cm3 = volume_mm3 / 1000.0
                    
                    return {
                        "success": True,
                        "length": float(length),
                        "width": float(width),
                        "thickness": float(thickness),
                        "volume_cm3": float(max(volume_cm3, 1.0)),
                        "source": "OpenCASCADE (Native STEP/IGES)"
                    }
                else:
                    return {"success": False, "error": "Kunde inte läsa in STEP/IGES-geometrin."}
            except ImportError:
                return {"success": False, "error": "OpenCASCADE-modul (pythonocc-core) saknas i Python-miljön."}
        else:
            return {"success": False, "error": f"Okänt filformat: .{ext}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}