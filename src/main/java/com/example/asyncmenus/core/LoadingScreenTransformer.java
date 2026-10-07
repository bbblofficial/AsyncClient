package com.example.asyncmenus.core;

import net.minecraft.launchwrapper.IClassTransformer;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.*;

/**
 * Neutralises LoadingScreenRenderer.drawScreen() so vanilla never
 * paints the Mojang splash. Our own renderer takes over from preInit.
 *
 * Forge 1.8.9 ships ASM 5.0.3, so we target ASM5.
 */
public class LoadingScreenTransformer implements IClassTransformer {

    private static final String TARGET = "net.minecraft.client.LoadingScreenRenderer";

    @Override
    public byte[] transform(String name, String transformedName, byte[] basicClass) {
        if (basicClass == null) return null;
        if (!TARGET.equals(transformedName) && !TARGET.equals(name)) return basicClass;

        ClassNode cn = new ClassNode();
        new ClassReader(basicClass).accept(cn, 0);

        for (MethodNode mn : cn.methods) {
            if ("drawScreen".equals(mn.name) || "func_73719_c".equals(mn.name)) {
                mn.instructions.clear();
                mn.tryCatchBlocks.clear();
                if (mn.localVariables != null) mn.localVariables.clear();

                InsnList ret = new InsnList();
                ret.add(new InsnNode(Opcodes.RETURN));
                mn.instructions.add(ret);

                mn.maxStack = 1;
                mn.maxLocals = 1;
            }
        }

        ClassWriter cw = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        cn.accept(cw);
        return cw.toByteArray();
    }
}
