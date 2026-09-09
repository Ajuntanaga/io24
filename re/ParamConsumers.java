// Find and decompile the code that CONSUMES the parameter descriptor tables and
// builds device commands. Targets:
//   1. functions referencing known parameter-table VAs
//   2. functions referencing route/format strings ("line/ch%d", component names)
//   3. functions referencing the bulk write path
// @category Analysis
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.address.Address;
import java.io.*;
import java.util.*;

public class ParamConsumers extends GhidraScript {

    static final long[] TABLE_VAS = {
        0x1800ea118L, 0x1800e9fd8L, 0x1800ea330L, 0x1800ecbe0L, 0x1800eaf18L,
        0x1800ef778L, 0x1800e9c20L, 0x1800ec490L, 0x1800ed3b8L, 0x1800ee778L,
        0x1800eec00L, 0x1800eee08L, 0x1800ef078L, 0x1800ef2e8L, 0x1800ebd98L,
        0x1800ece68L, 0x1800ed9f0L
    };
    static final String[] STR_MARKERS = {
        "line/ch%d", "JacksonGlobalComponent", "JacksonPresetComponent",
        "JacksonDiagnosticsComponent", "global", "diagnostics", "preset",
        "WriteBulkDataSync", "ExecuteCommand", "SendCommand"
    };

    String fullName(Function f) {
        try { return f.getName(true); } catch (Exception e) { return f.getName(); }
    }

    public void run() throws Exception {
        String[] args = getScriptArgs();
        String out = args.length > 0 ? args[0] : "/tmp/param_consumers.txt";

        FunctionManager fm = currentProgram.getFunctionManager();
        ReferenceManager rm = currentProgram.getReferenceManager();
        Listing listing = currentProgram.getListing();
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);

        LinkedHashMap<Address, Object[]> targets = new LinkedHashMap<>();

        // 1) xrefs to parameter tables
        for (long va : TABLE_VAS) {
            Address a = toAddr(va);
            for (Reference r : rm.getReferencesTo(a)) {
                Function f = fm.getFunctionContaining(r.getFromAddress());
                if (f != null) targets.putIfAbsent(f.getEntryPoint(),
                        new Object[]{f, "paramtable:" + Long.toHexString(va)});
            }
        }

        // 2) xrefs to marker strings
        DataIterator dit = listing.getDefinedData(true);
        while (dit.hasNext()) {
            Data d = dit.next();
            Object v;
            try { v = d.getValue(); } catch (Exception e) { continue; }
            if (!(v instanceof String)) continue;
            String s = (String) v;
            for (String m : STR_MARKERS) {
                if (s.equals(m) || (m.length() > 8 && s.contains(m))) {
                    for (Reference r : rm.getReferencesTo(d.getAddress())) {
                        Function f = fm.getFunctionContaining(r.getFromAddress());
                        if (f != null) targets.putIfAbsent(f.getEntryPoint(),
                                new Object[]{f, "str:" + s.substring(0, Math.min(40, s.length()))});
                    }
                    break;
                }
            }
        }

        println("[ParamConsumers] " + targets.size() + " target functions");
        PrintWriter pw = new PrintWriter(new FileWriter(out));
        pw.println("# functions consuming parameter tables / route strings");
        pw.println("# " + targets.size() + " functions\n");
        int n = 0;
        for (Map.Entry<Address, Object[]> e : targets.entrySet()) {
            Function f = (Function) e.getValue()[0];
            String why = (String) e.getValue()[1];
            String c;
            try {
                DecompileResults dr = di.decompileFunction(f, 120, monitor);
                c = (dr != null && dr.decompileCompleted())
                        ? dr.getDecompiledFunction().getC()
                        : "// <decompile failed>";
            } catch (Exception ex) { c = "// <exception " + ex + ">"; }
            pw.println("\n// ===== " + fullName(f) + " @ " + e.getKey() + "  [" + why + "] =====");
            pw.println(c);
            n++;
        }
        pw.close();
        println("[ParamConsumers] wrote " + n + " functions to " + out);
    }
}
