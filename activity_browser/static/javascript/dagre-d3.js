// dagre-d3-es 7.0.14 (esbuild IIFE, D3 from globalThis.d3)
var dagreD3 = (() => {
  var __create = Object.create;
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __getProtoOf = Object.getPrototypeOf;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __commonJS = (cb, mod) => function __require() {
    try {
      return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
    } catch (e) {
      throw mod = 0, e;
    }
  };
  var __export = (target, all) => {
    for (var name in all)
      __defProp(target, name, { get: all[name], enumerable: true });
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
    // If the importer is in node compatibility mode or this is not an ESM
    // file that has been converted to a CommonJS file using a Babel-
    // compatible transform (i.e. "__esModule" has not been set), then set
    // "default" to the CommonJS "module.exports" for node compatibility.
    isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
    mod
  ));
  var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

  // d3-global-shim.js
  var require_d3_global_shim = __commonJS({
    "d3-global-shim.js"(exports2, module2) {
      module2.exports = globalThis.d3;
    }
  });

  // node_modules/dagre-d3-es/src/index.js
  var index_exports = {};
  __export(index_exports, {
    graphlib: () => graphlib_exports,
    intersect: () => intersect_exports,
    render: () => render
  });

  // node_modules/dagre-d3-es/src/dagre-js/render.js
  var d38 = __toESM(require_d3_global_shim(), 1);

  // node_modules/lodash-es/_freeGlobal.js
  var freeGlobal = typeof global == "object" && global && global.Object === Object && global;
  var freeGlobal_default = freeGlobal;

  // node_modules/lodash-es/_root.js
  var freeSelf = typeof self == "object" && self && self.Object === Object && self;
  var root = freeGlobal_default || freeSelf || Function("return this")();
  var root_default = root;

  // node_modules/lodash-es/_Symbol.js
  var Symbol2 = root_default.Symbol;
  var Symbol_default = Symbol2;

  // node_modules/lodash-es/_getRawTag.js
  var objectProto = Object.prototype;
  var hasOwnProperty = objectProto.hasOwnProperty;
  var nativeObjectToString = objectProto.toString;
  var symToStringTag = Symbol_default ? Symbol_default.toStringTag : void 0;
  function getRawTag(value) {
    var isOwn = hasOwnProperty.call(value, symToStringTag), tag = value[symToStringTag];
    try {
      value[symToStringTag] = void 0;
      var unmasked = true;
    } catch (e) {
    }
    var result = nativeObjectToString.call(value);
    if (unmasked) {
      if (isOwn) {
        value[symToStringTag] = tag;
      } else {
        delete value[symToStringTag];
      }
    }
    return result;
  }
  var getRawTag_default = getRawTag;

  // node_modules/lodash-es/_objectToString.js
  var objectProto2 = Object.prototype;
  var nativeObjectToString2 = objectProto2.toString;
  function objectToString(value) {
    return nativeObjectToString2.call(value);
  }
  var objectToString_default = objectToString;

  // node_modules/lodash-es/_baseGetTag.js
  var nullTag = "[object Null]";
  var undefinedTag = "[object Undefined]";
  var symToStringTag2 = Symbol_default ? Symbol_default.toStringTag : void 0;
  function baseGetTag(value) {
    if (value == null) {
      return value === void 0 ? undefinedTag : nullTag;
    }
    return symToStringTag2 && symToStringTag2 in Object(value) ? getRawTag_default(value) : objectToString_default(value);
  }
  var baseGetTag_default = baseGetTag;

  // node_modules/lodash-es/isObjectLike.js
  function isObjectLike(value) {
    return value != null && typeof value == "object";
  }
  var isObjectLike_default = isObjectLike;

  // node_modules/lodash-es/isSymbol.js
  var symbolTag = "[object Symbol]";
  function isSymbol(value) {
    return typeof value == "symbol" || isObjectLike_default(value) && baseGetTag_default(value) == symbolTag;
  }
  var isSymbol_default = isSymbol;

  // node_modules/lodash-es/_arrayMap.js
  function arrayMap(array, iteratee) {
    var index = -1, length = array == null ? 0 : array.length, result = Array(length);
    while (++index < length) {
      result[index] = iteratee(array[index], index, array);
    }
    return result;
  }
  var arrayMap_default = arrayMap;

  // node_modules/lodash-es/isArray.js
  var isArray = Array.isArray;
  var isArray_default = isArray;

  // node_modules/lodash-es/_baseToString.js
  var INFINITY = 1 / 0;
  var symbolProto = Symbol_default ? Symbol_default.prototype : void 0;
  var symbolToString = symbolProto ? symbolProto.toString : void 0;
  function baseToString(value) {
    if (typeof value == "string") {
      return value;
    }
    if (isArray_default(value)) {
      return arrayMap_default(value, baseToString) + "";
    }
    if (isSymbol_default(value)) {
      return symbolToString ? symbolToString.call(value) : "";
    }
    var result = value + "";
    return result == "0" && 1 / value == -INFINITY ? "-0" : result;
  }
  var baseToString_default = baseToString;

  // node_modules/lodash-es/_trimmedEndIndex.js
  var reWhitespace = /\s/;
  function trimmedEndIndex(string) {
    var index = string.length;
    while (index-- && reWhitespace.test(string.charAt(index))) {
    }
    return index;
  }
  var trimmedEndIndex_default = trimmedEndIndex;

  // node_modules/lodash-es/_baseTrim.js
  var reTrimStart = /^\s+/;
  function baseTrim(string) {
    return string ? string.slice(0, trimmedEndIndex_default(string) + 1).replace(reTrimStart, "") : string;
  }
  var baseTrim_default = baseTrim;

  // node_modules/lodash-es/isObject.js
  function isObject(value) {
    var type = typeof value;
    return value != null && (type == "object" || type == "function");
  }
  var isObject_default = isObject;

  // node_modules/lodash-es/toNumber.js
  var NAN = 0 / 0;
  var reIsBadHex = /^[-+]0x[0-9a-f]+$/i;
  var reIsBinary = /^0b[01]+$/i;
  var reIsOctal = /^0o[0-7]+$/i;
  var freeParseInt = parseInt;
  function toNumber(value) {
    if (typeof value == "number") {
      return value;
    }
    if (isSymbol_default(value)) {
      return NAN;
    }
    if (isObject_default(value)) {
      var other = typeof value.valueOf == "function" ? value.valueOf() : value;
      value = isObject_default(other) ? other + "" : other;
    }
    if (typeof value != "string") {
      return value === 0 ? value : +value;
    }
    value = baseTrim_default(value);
    var isBinary = reIsBinary.test(value);
    return isBinary || reIsOctal.test(value) ? freeParseInt(value.slice(2), isBinary ? 2 : 8) : reIsBadHex.test(value) ? NAN : +value;
  }
  var toNumber_default = toNumber;

  // node_modules/lodash-es/toFinite.js
  var INFINITY2 = 1 / 0;
  var MAX_INTEGER = 17976931348623157e292;
  function toFinite(value) {
    if (!value) {
      return value === 0 ? value : 0;
    }
    value = toNumber_default(value);
    if (value === INFINITY2 || value === -INFINITY2) {
      var sign = value < 0 ? -1 : 1;
      return sign * MAX_INTEGER;
    }
    return value === value ? value : 0;
  }
  var toFinite_default = toFinite;

  // node_modules/lodash-es/toInteger.js
  function toInteger(value) {
    var result = toFinite_default(value), remainder = result % 1;
    return result === result ? remainder ? result - remainder : result : 0;
  }
  var toInteger_default = toInteger;

  // node_modules/lodash-es/identity.js
  function identity(value) {
    return value;
  }
  var identity_default = identity;

  // node_modules/lodash-es/isFunction.js
  var asyncTag = "[object AsyncFunction]";
  var funcTag = "[object Function]";
  var genTag = "[object GeneratorFunction]";
  var proxyTag = "[object Proxy]";
  function isFunction(value) {
    if (!isObject_default(value)) {
      return false;
    }
    var tag = baseGetTag_default(value);
    return tag == funcTag || tag == genTag || tag == asyncTag || tag == proxyTag;
  }
  var isFunction_default = isFunction;

  // node_modules/lodash-es/_coreJsData.js
  var coreJsData = root_default["__core-js_shared__"];
  var coreJsData_default = coreJsData;

  // node_modules/lodash-es/_isMasked.js
  var maskSrcKey = (function() {
    var uid = /[^.]+$/.exec(coreJsData_default && coreJsData_default.keys && coreJsData_default.keys.IE_PROTO || "");
    return uid ? "Symbol(src)_1." + uid : "";
  })();
  function isMasked(func) {
    return !!maskSrcKey && maskSrcKey in func;
  }
  var isMasked_default = isMasked;

  // node_modules/lodash-es/_toSource.js
  var funcProto = Function.prototype;
  var funcToString = funcProto.toString;
  function toSource(func) {
    if (func != null) {
      try {
        return funcToString.call(func);
      } catch (e) {
      }
      try {
        return func + "";
      } catch (e) {
      }
    }
    return "";
  }
  var toSource_default = toSource;

  // node_modules/lodash-es/_baseIsNative.js
  var reRegExpChar = /[\\^$.*+?()[\]{}|]/g;
  var reIsHostCtor = /^\[object .+?Constructor\]$/;
  var funcProto2 = Function.prototype;
  var objectProto3 = Object.prototype;
  var funcToString2 = funcProto2.toString;
  var hasOwnProperty2 = objectProto3.hasOwnProperty;
  var reIsNative = RegExp(
    "^" + funcToString2.call(hasOwnProperty2).replace(reRegExpChar, "\\$&").replace(/hasOwnProperty|(function).*?(?=\\\()| for .+?(?=\\\])/g, "$1.*?") + "$"
  );
  function baseIsNative(value) {
    if (!isObject_default(value) || isMasked_default(value)) {
      return false;
    }
    var pattern = isFunction_default(value) ? reIsNative : reIsHostCtor;
    return pattern.test(toSource_default(value));
  }
  var baseIsNative_default = baseIsNative;

  // node_modules/lodash-es/_getValue.js
  function getValue(object, key) {
    return object == null ? void 0 : object[key];
  }
  var getValue_default = getValue;

  // node_modules/lodash-es/_getNative.js
  function getNative(object, key) {
    var value = getValue_default(object, key);
    return baseIsNative_default(value) ? value : void 0;
  }
  var getNative_default = getNative;

  // node_modules/lodash-es/_WeakMap.js
  var WeakMap = getNative_default(root_default, "WeakMap");
  var WeakMap_default = WeakMap;

  // node_modules/lodash-es/_baseCreate.js
  var objectCreate = Object.create;
  var baseCreate = /* @__PURE__ */ (function() {
    function object() {
    }
    return function(proto) {
      if (!isObject_default(proto)) {
        return {};
      }
      if (objectCreate) {
        return objectCreate(proto);
      }
      object.prototype = proto;
      var result = new object();
      object.prototype = void 0;
      return result;
    };
  })();
  var baseCreate_default = baseCreate;

  // node_modules/lodash-es/_apply.js
  function apply(func, thisArg, args) {
    switch (args.length) {
      case 0:
        return func.call(thisArg);
      case 1:
        return func.call(thisArg, args[0]);
      case 2:
        return func.call(thisArg, args[0], args[1]);
      case 3:
        return func.call(thisArg, args[0], args[1], args[2]);
    }
    return func.apply(thisArg, args);
  }
  var apply_default = apply;

  // node_modules/lodash-es/noop.js
  function noop() {
  }
  var noop_default = noop;

  // node_modules/lodash-es/_copyArray.js
  function copyArray(source, array) {
    var index = -1, length = source.length;
    array || (array = Array(length));
    while (++index < length) {
      array[index] = source[index];
    }
    return array;
  }
  var copyArray_default = copyArray;

  // node_modules/lodash-es/_shortOut.js
  var HOT_COUNT = 800;
  var HOT_SPAN = 16;
  var nativeNow = Date.now;
  function shortOut(func) {
    var count = 0, lastCalled = 0;
    return function() {
      var stamp = nativeNow(), remaining = HOT_SPAN - (stamp - lastCalled);
      lastCalled = stamp;
      if (remaining > 0) {
        if (++count >= HOT_COUNT) {
          return arguments[0];
        }
      } else {
        count = 0;
      }
      return func.apply(void 0, arguments);
    };
  }
  var shortOut_default = shortOut;

  // node_modules/lodash-es/constant.js
  function constant(value) {
    return function() {
      return value;
    };
  }
  var constant_default = constant;

  // node_modules/lodash-es/_defineProperty.js
  var defineProperty = (function() {
    try {
      var func = getNative_default(Object, "defineProperty");
      func({}, "", {});
      return func;
    } catch (e) {
    }
  })();
  var defineProperty_default = defineProperty;

  // node_modules/lodash-es/_baseSetToString.js
  var baseSetToString = !defineProperty_default ? identity_default : function(func, string) {
    return defineProperty_default(func, "toString", {
      "configurable": true,
      "enumerable": false,
      "value": constant_default(string),
      "writable": true
    });
  };
  var baseSetToString_default = baseSetToString;

  // node_modules/lodash-es/_setToString.js
  var setToString = shortOut_default(baseSetToString_default);
  var setToString_default = setToString;

  // node_modules/lodash-es/_arrayEach.js
  function arrayEach(array, iteratee) {
    var index = -1, length = array == null ? 0 : array.length;
    while (++index < length) {
      if (iteratee(array[index], index, array) === false) {
        break;
      }
    }
    return array;
  }
  var arrayEach_default = arrayEach;

  // node_modules/lodash-es/_baseFindIndex.js
  function baseFindIndex(array, predicate, fromIndex, fromRight) {
    var length = array.length, index = fromIndex + (fromRight ? 1 : -1);
    while (fromRight ? index-- : ++index < length) {
      if (predicate(array[index], index, array)) {
        return index;
      }
    }
    return -1;
  }
  var baseFindIndex_default = baseFindIndex;

  // node_modules/lodash-es/_baseIsNaN.js
  function baseIsNaN(value) {
    return value !== value;
  }
  var baseIsNaN_default = baseIsNaN;

  // node_modules/lodash-es/_strictIndexOf.js
  function strictIndexOf(array, value, fromIndex) {
    var index = fromIndex - 1, length = array.length;
    while (++index < length) {
      if (array[index] === value) {
        return index;
      }
    }
    return -1;
  }
  var strictIndexOf_default = strictIndexOf;

  // node_modules/lodash-es/_baseIndexOf.js
  function baseIndexOf(array, value, fromIndex) {
    return value === value ? strictIndexOf_default(array, value, fromIndex) : baseFindIndex_default(array, baseIsNaN_default, fromIndex);
  }
  var baseIndexOf_default = baseIndexOf;

  // node_modules/lodash-es/_arrayIncludes.js
  function arrayIncludes(array, value) {
    var length = array == null ? 0 : array.length;
    return !!length && baseIndexOf_default(array, value, 0) > -1;
  }
  var arrayIncludes_default = arrayIncludes;

  // node_modules/lodash-es/_isIndex.js
  var MAX_SAFE_INTEGER = 9007199254740991;
  var reIsUint = /^(?:0|[1-9]\d*)$/;
  function isIndex(value, length) {
    var type = typeof value;
    length = length == null ? MAX_SAFE_INTEGER : length;
    return !!length && (type == "number" || type != "symbol" && reIsUint.test(value)) && (value > -1 && value % 1 == 0 && value < length);
  }
  var isIndex_default = isIndex;

  // node_modules/lodash-es/_baseAssignValue.js
  function baseAssignValue(object, key, value) {
    if (key == "__proto__" && defineProperty_default) {
      defineProperty_default(object, key, {
        "configurable": true,
        "enumerable": true,
        "value": value,
        "writable": true
      });
    } else {
      object[key] = value;
    }
  }
  var baseAssignValue_default = baseAssignValue;

  // node_modules/lodash-es/eq.js
  function eq(value, other) {
    return value === other || value !== value && other !== other;
  }
  var eq_default = eq;

  // node_modules/lodash-es/_assignValue.js
  var objectProto4 = Object.prototype;
  var hasOwnProperty3 = objectProto4.hasOwnProperty;
  function assignValue(object, key, value) {
    var objValue = object[key];
    if (!(hasOwnProperty3.call(object, key) && eq_default(objValue, value)) || value === void 0 && !(key in object)) {
      baseAssignValue_default(object, key, value);
    }
  }
  var assignValue_default = assignValue;

  // node_modules/lodash-es/_copyObject.js
  function copyObject(source, props, object, customizer) {
    var isNew = !object;
    object || (object = {});
    var index = -1, length = props.length;
    while (++index < length) {
      var key = props[index];
      var newValue = customizer ? customizer(object[key], source[key], key, object, source) : void 0;
      if (newValue === void 0) {
        newValue = source[key];
      }
      if (isNew) {
        baseAssignValue_default(object, key, newValue);
      } else {
        assignValue_default(object, key, newValue);
      }
    }
    return object;
  }
  var copyObject_default = copyObject;

  // node_modules/lodash-es/_overRest.js
  var nativeMax = Math.max;
  function overRest(func, start, transform) {
    start = nativeMax(start === void 0 ? func.length - 1 : start, 0);
    return function() {
      var args = arguments, index = -1, length = nativeMax(args.length - start, 0), array = Array(length);
      while (++index < length) {
        array[index] = args[start + index];
      }
      index = -1;
      var otherArgs = Array(start + 1);
      while (++index < start) {
        otherArgs[index] = args[index];
      }
      otherArgs[start] = transform(array);
      return apply_default(func, this, otherArgs);
    };
  }
  var overRest_default = overRest;

  // node_modules/lodash-es/_baseRest.js
  function baseRest(func, start) {
    return setToString_default(overRest_default(func, start, identity_default), func + "");
  }
  var baseRest_default = baseRest;

  // node_modules/lodash-es/isLength.js
  var MAX_SAFE_INTEGER2 = 9007199254740991;
  function isLength(value) {
    return typeof value == "number" && value > -1 && value % 1 == 0 && value <= MAX_SAFE_INTEGER2;
  }
  var isLength_default = isLength;

  // node_modules/lodash-es/isArrayLike.js
  function isArrayLike(value) {
    return value != null && isLength_default(value.length) && !isFunction_default(value);
  }
  var isArrayLike_default = isArrayLike;

  // node_modules/lodash-es/_isIterateeCall.js
  function isIterateeCall(value, index, object) {
    if (!isObject_default(object)) {
      return false;
    }
    var type = typeof index;
    if (type == "number" ? isArrayLike_default(object) && isIndex_default(index, object.length) : type == "string" && index in object) {
      return eq_default(object[index], value);
    }
    return false;
  }
  var isIterateeCall_default = isIterateeCall;

  // node_modules/lodash-es/_createAssigner.js
  function createAssigner(assigner) {
    return baseRest_default(function(object, sources) {
      var index = -1, length = sources.length, customizer = length > 1 ? sources[length - 1] : void 0, guard = length > 2 ? sources[2] : void 0;
      customizer = assigner.length > 3 && typeof customizer == "function" ? (length--, customizer) : void 0;
      if (guard && isIterateeCall_default(sources[0], sources[1], guard)) {
        customizer = length < 3 ? void 0 : customizer;
        length = 1;
      }
      object = Object(object);
      while (++index < length) {
        var source = sources[index];
        if (source) {
          assigner(object, source, index, customizer);
        }
      }
      return object;
    });
  }
  var createAssigner_default = createAssigner;

  // node_modules/lodash-es/_isPrototype.js
  var objectProto5 = Object.prototype;
  function isPrototype(value) {
    var Ctor = value && value.constructor, proto = typeof Ctor == "function" && Ctor.prototype || objectProto5;
    return value === proto;
  }
  var isPrototype_default = isPrototype;

  // node_modules/lodash-es/_baseTimes.js
  function baseTimes(n, iteratee) {
    var index = -1, result = Array(n);
    while (++index < n) {
      result[index] = iteratee(index);
    }
    return result;
  }
  var baseTimes_default = baseTimes;

  // node_modules/lodash-es/_baseIsArguments.js
  var argsTag = "[object Arguments]";
  function baseIsArguments(value) {
    return isObjectLike_default(value) && baseGetTag_default(value) == argsTag;
  }
  var baseIsArguments_default = baseIsArguments;

  // node_modules/lodash-es/isArguments.js
  var objectProto6 = Object.prototype;
  var hasOwnProperty4 = objectProto6.hasOwnProperty;
  var propertyIsEnumerable = objectProto6.propertyIsEnumerable;
  var isArguments = baseIsArguments_default(/* @__PURE__ */ (function() {
    return arguments;
  })()) ? baseIsArguments_default : function(value) {
    return isObjectLike_default(value) && hasOwnProperty4.call(value, "callee") && !propertyIsEnumerable.call(value, "callee");
  };
  var isArguments_default = isArguments;

  // node_modules/lodash-es/stubFalse.js
  function stubFalse() {
    return false;
  }
  var stubFalse_default = stubFalse;

  // node_modules/lodash-es/isBuffer.js
  var freeExports = typeof exports == "object" && exports && !exports.nodeType && exports;
  var freeModule = freeExports && typeof module == "object" && module && !module.nodeType && module;
  var moduleExports = freeModule && freeModule.exports === freeExports;
  var Buffer2 = moduleExports ? root_default.Buffer : void 0;
  var nativeIsBuffer = Buffer2 ? Buffer2.isBuffer : void 0;
  var isBuffer = nativeIsBuffer || stubFalse_default;
  var isBuffer_default = isBuffer;

  // node_modules/lodash-es/_baseIsTypedArray.js
  var argsTag2 = "[object Arguments]";
  var arrayTag = "[object Array]";
  var boolTag = "[object Boolean]";
  var dateTag = "[object Date]";
  var errorTag = "[object Error]";
  var funcTag2 = "[object Function]";
  var mapTag = "[object Map]";
  var numberTag = "[object Number]";
  var objectTag = "[object Object]";
  var regexpTag = "[object RegExp]";
  var setTag = "[object Set]";
  var stringTag = "[object String]";
  var weakMapTag = "[object WeakMap]";
  var arrayBufferTag = "[object ArrayBuffer]";
  var dataViewTag = "[object DataView]";
  var float32Tag = "[object Float32Array]";
  var float64Tag = "[object Float64Array]";
  var int8Tag = "[object Int8Array]";
  var int16Tag = "[object Int16Array]";
  var int32Tag = "[object Int32Array]";
  var uint8Tag = "[object Uint8Array]";
  var uint8ClampedTag = "[object Uint8ClampedArray]";
  var uint16Tag = "[object Uint16Array]";
  var uint32Tag = "[object Uint32Array]";
  var typedArrayTags = {};
  typedArrayTags[float32Tag] = typedArrayTags[float64Tag] = typedArrayTags[int8Tag] = typedArrayTags[int16Tag] = typedArrayTags[int32Tag] = typedArrayTags[uint8Tag] = typedArrayTags[uint8ClampedTag] = typedArrayTags[uint16Tag] = typedArrayTags[uint32Tag] = true;
  typedArrayTags[argsTag2] = typedArrayTags[arrayTag] = typedArrayTags[arrayBufferTag] = typedArrayTags[boolTag] = typedArrayTags[dataViewTag] = typedArrayTags[dateTag] = typedArrayTags[errorTag] = typedArrayTags[funcTag2] = typedArrayTags[mapTag] = typedArrayTags[numberTag] = typedArrayTags[objectTag] = typedArrayTags[regexpTag] = typedArrayTags[setTag] = typedArrayTags[stringTag] = typedArrayTags[weakMapTag] = false;
  function baseIsTypedArray(value) {
    return isObjectLike_default(value) && isLength_default(value.length) && !!typedArrayTags[baseGetTag_default(value)];
  }
  var baseIsTypedArray_default = baseIsTypedArray;

  // node_modules/lodash-es/_baseUnary.js
  function baseUnary(func) {
    return function(value) {
      return func(value);
    };
  }
  var baseUnary_default = baseUnary;

  // node_modules/lodash-es/_nodeUtil.js
  var freeExports2 = typeof exports == "object" && exports && !exports.nodeType && exports;
  var freeModule2 = freeExports2 && typeof module == "object" && module && !module.nodeType && module;
  var moduleExports2 = freeModule2 && freeModule2.exports === freeExports2;
  var freeProcess = moduleExports2 && freeGlobal_default.process;
  var nodeUtil = (function() {
    try {
      var types = freeModule2 && freeModule2.require && freeModule2.require("util").types;
      if (types) {
        return types;
      }
      return freeProcess && freeProcess.binding && freeProcess.binding("util");
    } catch (e) {
    }
  })();
  var nodeUtil_default = nodeUtil;

  // node_modules/lodash-es/isTypedArray.js
  var nodeIsTypedArray = nodeUtil_default && nodeUtil_default.isTypedArray;
  var isTypedArray = nodeIsTypedArray ? baseUnary_default(nodeIsTypedArray) : baseIsTypedArray_default;
  var isTypedArray_default = isTypedArray;

  // node_modules/lodash-es/_arrayLikeKeys.js
  var objectProto7 = Object.prototype;
  var hasOwnProperty5 = objectProto7.hasOwnProperty;
  function arrayLikeKeys(value, inherited) {
    var isArr = isArray_default(value), isArg = !isArr && isArguments_default(value), isBuff = !isArr && !isArg && isBuffer_default(value), isType = !isArr && !isArg && !isBuff && isTypedArray_default(value), skipIndexes = isArr || isArg || isBuff || isType, result = skipIndexes ? baseTimes_default(value.length, String) : [], length = result.length;
    for (var key in value) {
      if ((inherited || hasOwnProperty5.call(value, key)) && !(skipIndexes && // Safari 9 has enumerable `arguments.length` in strict mode.
      (key == "length" || // Node.js 0.10 has enumerable non-index properties on buffers.
      isBuff && (key == "offset" || key == "parent") || // PhantomJS 2 has enumerable non-index properties on typed arrays.
      isType && (key == "buffer" || key == "byteLength" || key == "byteOffset") || // Skip index properties.
      isIndex_default(key, length)))) {
        result.push(key);
      }
    }
    return result;
  }
  var arrayLikeKeys_default = arrayLikeKeys;

  // node_modules/lodash-es/_overArg.js
  function overArg(func, transform) {
    return function(arg) {
      return func(transform(arg));
    };
  }
  var overArg_default = overArg;

  // node_modules/lodash-es/_nativeKeys.js
  var nativeKeys = overArg_default(Object.keys, Object);
  var nativeKeys_default = nativeKeys;

  // node_modules/lodash-es/_baseKeys.js
  var objectProto8 = Object.prototype;
  var hasOwnProperty6 = objectProto8.hasOwnProperty;
  function baseKeys(object) {
    if (!isPrototype_default(object)) {
      return nativeKeys_default(object);
    }
    var result = [];
    for (var key in Object(object)) {
      if (hasOwnProperty6.call(object, key) && key != "constructor") {
        result.push(key);
      }
    }
    return result;
  }
  var baseKeys_default = baseKeys;

  // node_modules/lodash-es/keys.js
  function keys(object) {
    return isArrayLike_default(object) ? arrayLikeKeys_default(object) : baseKeys_default(object);
  }
  var keys_default = keys;

  // node_modules/lodash-es/_nativeKeysIn.js
  function nativeKeysIn(object) {
    var result = [];
    if (object != null) {
      for (var key in Object(object)) {
        result.push(key);
      }
    }
    return result;
  }
  var nativeKeysIn_default = nativeKeysIn;

  // node_modules/lodash-es/_baseKeysIn.js
  var objectProto9 = Object.prototype;
  var hasOwnProperty7 = objectProto9.hasOwnProperty;
  function baseKeysIn(object) {
    if (!isObject_default(object)) {
      return nativeKeysIn_default(object);
    }
    var isProto = isPrototype_default(object), result = [];
    for (var key in object) {
      if (!(key == "constructor" && (isProto || !hasOwnProperty7.call(object, key)))) {
        result.push(key);
      }
    }
    return result;
  }
  var baseKeysIn_default = baseKeysIn;

  // node_modules/lodash-es/keysIn.js
  function keysIn(object) {
    return isArrayLike_default(object) ? arrayLikeKeys_default(object, true) : baseKeysIn_default(object);
  }
  var keysIn_default = keysIn;

  // node_modules/lodash-es/_isKey.js
  var reIsDeepProp = /\.|\[(?:[^[\]]*|(["'])(?:(?!\1)[^\\]|\\.)*?\1)\]/;
  var reIsPlainProp = /^\w*$/;
  function isKey(value, object) {
    if (isArray_default(value)) {
      return false;
    }
    var type = typeof value;
    if (type == "number" || type == "symbol" || type == "boolean" || value == null || isSymbol_default(value)) {
      return true;
    }
    return reIsPlainProp.test(value) || !reIsDeepProp.test(value) || object != null && value in Object(object);
  }
  var isKey_default = isKey;

  // node_modules/lodash-es/_nativeCreate.js
  var nativeCreate = getNative_default(Object, "create");
  var nativeCreate_default = nativeCreate;

  // node_modules/lodash-es/_hashClear.js
  function hashClear() {
    this.__data__ = nativeCreate_default ? nativeCreate_default(null) : {};
    this.size = 0;
  }
  var hashClear_default = hashClear;

  // node_modules/lodash-es/_hashDelete.js
  function hashDelete(key) {
    var result = this.has(key) && delete this.__data__[key];
    this.size -= result ? 1 : 0;
    return result;
  }
  var hashDelete_default = hashDelete;

  // node_modules/lodash-es/_hashGet.js
  var HASH_UNDEFINED = "__lodash_hash_undefined__";
  var objectProto10 = Object.prototype;
  var hasOwnProperty8 = objectProto10.hasOwnProperty;
  function hashGet(key) {
    var data = this.__data__;
    if (nativeCreate_default) {
      var result = data[key];
      return result === HASH_UNDEFINED ? void 0 : result;
    }
    return hasOwnProperty8.call(data, key) ? data[key] : void 0;
  }
  var hashGet_default = hashGet;

  // node_modules/lodash-es/_hashHas.js
  var objectProto11 = Object.prototype;
  var hasOwnProperty9 = objectProto11.hasOwnProperty;
  function hashHas(key) {
    var data = this.__data__;
    return nativeCreate_default ? data[key] !== void 0 : hasOwnProperty9.call(data, key);
  }
  var hashHas_default = hashHas;

  // node_modules/lodash-es/_hashSet.js
  var HASH_UNDEFINED2 = "__lodash_hash_undefined__";
  function hashSet(key, value) {
    var data = this.__data__;
    this.size += this.has(key) ? 0 : 1;
    data[key] = nativeCreate_default && value === void 0 ? HASH_UNDEFINED2 : value;
    return this;
  }
  var hashSet_default = hashSet;

  // node_modules/lodash-es/_Hash.js
  function Hash(entries) {
    var index = -1, length = entries == null ? 0 : entries.length;
    this.clear();
    while (++index < length) {
      var entry = entries[index];
      this.set(entry[0], entry[1]);
    }
  }
  Hash.prototype.clear = hashClear_default;
  Hash.prototype["delete"] = hashDelete_default;
  Hash.prototype.get = hashGet_default;
  Hash.prototype.has = hashHas_default;
  Hash.prototype.set = hashSet_default;
  var Hash_default = Hash;

  // node_modules/lodash-es/_listCacheClear.js
  function listCacheClear() {
    this.__data__ = [];
    this.size = 0;
  }
  var listCacheClear_default = listCacheClear;

  // node_modules/lodash-es/_assocIndexOf.js
  function assocIndexOf(array, key) {
    var length = array.length;
    while (length--) {
      if (eq_default(array[length][0], key)) {
        return length;
      }
    }
    return -1;
  }
  var assocIndexOf_default = assocIndexOf;

  // node_modules/lodash-es/_listCacheDelete.js
  var arrayProto = Array.prototype;
  var splice = arrayProto.splice;
  function listCacheDelete(key) {
    var data = this.__data__, index = assocIndexOf_default(data, key);
    if (index < 0) {
      return false;
    }
    var lastIndex = data.length - 1;
    if (index == lastIndex) {
      data.pop();
    } else {
      splice.call(data, index, 1);
    }
    --this.size;
    return true;
  }
  var listCacheDelete_default = listCacheDelete;

  // node_modules/lodash-es/_listCacheGet.js
  function listCacheGet(key) {
    var data = this.__data__, index = assocIndexOf_default(data, key);
    return index < 0 ? void 0 : data[index][1];
  }
  var listCacheGet_default = listCacheGet;

  // node_modules/lodash-es/_listCacheHas.js
  function listCacheHas(key) {
    return assocIndexOf_default(this.__data__, key) > -1;
  }
  var listCacheHas_default = listCacheHas;

  // node_modules/lodash-es/_listCacheSet.js
  function listCacheSet(key, value) {
    var data = this.__data__, index = assocIndexOf_default(data, key);
    if (index < 0) {
      ++this.size;
      data.push([key, value]);
    } else {
      data[index][1] = value;
    }
    return this;
  }
  var listCacheSet_default = listCacheSet;

  // node_modules/lodash-es/_ListCache.js
  function ListCache(entries) {
    var index = -1, length = entries == null ? 0 : entries.length;
    this.clear();
    while (++index < length) {
      var entry = entries[index];
      this.set(entry[0], entry[1]);
    }
  }
  ListCache.prototype.clear = listCacheClear_default;
  ListCache.prototype["delete"] = listCacheDelete_default;
  ListCache.prototype.get = listCacheGet_default;
  ListCache.prototype.has = listCacheHas_default;
  ListCache.prototype.set = listCacheSet_default;
  var ListCache_default = ListCache;

  // node_modules/lodash-es/_Map.js
  var Map = getNative_default(root_default, "Map");
  var Map_default = Map;

  // node_modules/lodash-es/_mapCacheClear.js
  function mapCacheClear() {
    this.size = 0;
    this.__data__ = {
      "hash": new Hash_default(),
      "map": new (Map_default || ListCache_default)(),
      "string": new Hash_default()
    };
  }
  var mapCacheClear_default = mapCacheClear;

  // node_modules/lodash-es/_isKeyable.js
  function isKeyable(value) {
    var type = typeof value;
    return type == "string" || type == "number" || type == "symbol" || type == "boolean" ? value !== "__proto__" : value === null;
  }
  var isKeyable_default = isKeyable;

  // node_modules/lodash-es/_getMapData.js
  function getMapData(map2, key) {
    var data = map2.__data__;
    return isKeyable_default(key) ? data[typeof key == "string" ? "string" : "hash"] : data.map;
  }
  var getMapData_default = getMapData;

  // node_modules/lodash-es/_mapCacheDelete.js
  function mapCacheDelete(key) {
    var result = getMapData_default(this, key)["delete"](key);
    this.size -= result ? 1 : 0;
    return result;
  }
  var mapCacheDelete_default = mapCacheDelete;

  // node_modules/lodash-es/_mapCacheGet.js
  function mapCacheGet(key) {
    return getMapData_default(this, key).get(key);
  }
  var mapCacheGet_default = mapCacheGet;

  // node_modules/lodash-es/_mapCacheHas.js
  function mapCacheHas(key) {
    return getMapData_default(this, key).has(key);
  }
  var mapCacheHas_default = mapCacheHas;

  // node_modules/lodash-es/_mapCacheSet.js
  function mapCacheSet(key, value) {
    var data = getMapData_default(this, key), size2 = data.size;
    data.set(key, value);
    this.size += data.size == size2 ? 0 : 1;
    return this;
  }
  var mapCacheSet_default = mapCacheSet;

  // node_modules/lodash-es/_MapCache.js
  function MapCache(entries) {
    var index = -1, length = entries == null ? 0 : entries.length;
    this.clear();
    while (++index < length) {
      var entry = entries[index];
      this.set(entry[0], entry[1]);
    }
  }
  MapCache.prototype.clear = mapCacheClear_default;
  MapCache.prototype["delete"] = mapCacheDelete_default;
  MapCache.prototype.get = mapCacheGet_default;
  MapCache.prototype.has = mapCacheHas_default;
  MapCache.prototype.set = mapCacheSet_default;
  var MapCache_default = MapCache;

  // node_modules/lodash-es/memoize.js
  var FUNC_ERROR_TEXT = "Expected a function";
  function memoize(func, resolver) {
    if (typeof func != "function" || resolver != null && typeof resolver != "function") {
      throw new TypeError(FUNC_ERROR_TEXT);
    }
    var memoized = function() {
      var args = arguments, key = resolver ? resolver.apply(this, args) : args[0], cache = memoized.cache;
      if (cache.has(key)) {
        return cache.get(key);
      }
      var result = func.apply(this, args);
      memoized.cache = cache.set(key, result) || cache;
      return result;
    };
    memoized.cache = new (memoize.Cache || MapCache_default)();
    return memoized;
  }
  memoize.Cache = MapCache_default;
  var memoize_default = memoize;

  // node_modules/lodash-es/_memoizeCapped.js
  var MAX_MEMOIZE_SIZE = 500;
  function memoizeCapped(func) {
    var result = memoize_default(func, function(key) {
      if (cache.size === MAX_MEMOIZE_SIZE) {
        cache.clear();
      }
      return key;
    });
    var cache = result.cache;
    return result;
  }
  var memoizeCapped_default = memoizeCapped;

  // node_modules/lodash-es/_stringToPath.js
  var rePropName = /[^.[\]]+|\[(?:(-?\d+(?:\.\d+)?)|(["'])((?:(?!\2)[^\\]|\\.)*?)\2)\]|(?=(?:\.|\[\])(?:\.|\[\]|$))/g;
  var reEscapeChar = /\\(\\)?/g;
  var stringToPath = memoizeCapped_default(function(string) {
    var result = [];
    if (string.charCodeAt(0) === 46) {
      result.push("");
    }
    string.replace(rePropName, function(match, number, quote, subString) {
      result.push(quote ? subString.replace(reEscapeChar, "$1") : number || match);
    });
    return result;
  });
  var stringToPath_default = stringToPath;

  // node_modules/lodash-es/toString.js
  function toString(value) {
    return value == null ? "" : baseToString_default(value);
  }
  var toString_default = toString;

  // node_modules/lodash-es/_castPath.js
  function castPath(value, object) {
    if (isArray_default(value)) {
      return value;
    }
    return isKey_default(value, object) ? [value] : stringToPath_default(toString_default(value));
  }
  var castPath_default = castPath;

  // node_modules/lodash-es/_toKey.js
  var INFINITY3 = 1 / 0;
  function toKey(value) {
    if (typeof value == "string" || isSymbol_default(value)) {
      return value;
    }
    var result = value + "";
    return result == "0" && 1 / value == -INFINITY3 ? "-0" : result;
  }
  var toKey_default = toKey;

  // node_modules/lodash-es/_baseGet.js
  function baseGet(object, path) {
    path = castPath_default(path, object);
    var index = 0, length = path.length;
    while (object != null && index < length) {
      object = object[toKey_default(path[index++])];
    }
    return index && index == length ? object : void 0;
  }
  var baseGet_default = baseGet;

  // node_modules/lodash-es/get.js
  function get(object, path, defaultValue) {
    var result = object == null ? void 0 : baseGet_default(object, path);
    return result === void 0 ? defaultValue : result;
  }
  var get_default = get;

  // node_modules/lodash-es/_arrayPush.js
  function arrayPush(array, values2) {
    var index = -1, length = values2.length, offset = array.length;
    while (++index < length) {
      array[offset + index] = values2[index];
    }
    return array;
  }
  var arrayPush_default = arrayPush;

  // node_modules/lodash-es/_isFlattenable.js
  var spreadableSymbol = Symbol_default ? Symbol_default.isConcatSpreadable : void 0;
  function isFlattenable(value) {
    return isArray_default(value) || isArguments_default(value) || !!(spreadableSymbol && value && value[spreadableSymbol]);
  }
  var isFlattenable_default = isFlattenable;

  // node_modules/lodash-es/_baseFlatten.js
  function baseFlatten(array, depth, predicate, isStrict, result) {
    var index = -1, length = array.length;
    predicate || (predicate = isFlattenable_default);
    result || (result = []);
    while (++index < length) {
      var value = array[index];
      if (depth > 0 && predicate(value)) {
        if (depth > 1) {
          baseFlatten(value, depth - 1, predicate, isStrict, result);
        } else {
          arrayPush_default(result, value);
        }
      } else if (!isStrict) {
        result[result.length] = value;
      }
    }
    return result;
  }
  var baseFlatten_default = baseFlatten;

  // node_modules/lodash-es/flatten.js
  function flatten(array) {
    var length = array == null ? 0 : array.length;
    return length ? baseFlatten_default(array, 1) : [];
  }
  var flatten_default = flatten;

  // node_modules/lodash-es/_flatRest.js
  function flatRest(func) {
    return setToString_default(overRest_default(func, void 0, flatten_default), func + "");
  }
  var flatRest_default = flatRest;

  // node_modules/lodash-es/_getPrototype.js
  var getPrototype = overArg_default(Object.getPrototypeOf, Object);
  var getPrototype_default = getPrototype;

  // node_modules/lodash-es/isPlainObject.js
  var objectTag2 = "[object Object]";
  var funcProto3 = Function.prototype;
  var objectProto12 = Object.prototype;
  var funcToString3 = funcProto3.toString;
  var hasOwnProperty10 = objectProto12.hasOwnProperty;
  var objectCtorString = funcToString3.call(Object);
  function isPlainObject(value) {
    if (!isObjectLike_default(value) || baseGetTag_default(value) != objectTag2) {
      return false;
    }
    var proto = getPrototype_default(value);
    if (proto === null) {
      return true;
    }
    var Ctor = hasOwnProperty10.call(proto, "constructor") && proto.constructor;
    return typeof Ctor == "function" && Ctor instanceof Ctor && funcToString3.call(Ctor) == objectCtorString;
  }
  var isPlainObject_default = isPlainObject;

  // node_modules/lodash-es/_hasUnicode.js
  var rsAstralRange = "\\ud800-\\udfff";
  var rsComboMarksRange = "\\u0300-\\u036f";
  var reComboHalfMarksRange = "\\ufe20-\\ufe2f";
  var rsComboSymbolsRange = "\\u20d0-\\u20ff";
  var rsComboRange = rsComboMarksRange + reComboHalfMarksRange + rsComboSymbolsRange;
  var rsVarRange = "\\ufe0e\\ufe0f";
  var rsZWJ = "\\u200d";
  var reHasUnicode = RegExp("[" + rsZWJ + rsAstralRange + rsComboRange + rsVarRange + "]");
  function hasUnicode(string) {
    return reHasUnicode.test(string);
  }
  var hasUnicode_default = hasUnicode;

  // node_modules/lodash-es/_arrayReduce.js
  function arrayReduce(array, iteratee, accumulator, initAccum) {
    var index = -1, length = array == null ? 0 : array.length;
    if (initAccum && length) {
      accumulator = array[++index];
    }
    while (++index < length) {
      accumulator = iteratee(accumulator, array[index], index, array);
    }
    return accumulator;
  }
  var arrayReduce_default = arrayReduce;

  // node_modules/lodash-es/_stackClear.js
  function stackClear() {
    this.__data__ = new ListCache_default();
    this.size = 0;
  }
  var stackClear_default = stackClear;

  // node_modules/lodash-es/_stackDelete.js
  function stackDelete(key) {
    var data = this.__data__, result = data["delete"](key);
    this.size = data.size;
    return result;
  }
  var stackDelete_default = stackDelete;

  // node_modules/lodash-es/_stackGet.js
  function stackGet(key) {
    return this.__data__.get(key);
  }
  var stackGet_default = stackGet;

  // node_modules/lodash-es/_stackHas.js
  function stackHas(key) {
    return this.__data__.has(key);
  }
  var stackHas_default = stackHas;

  // node_modules/lodash-es/_stackSet.js
  var LARGE_ARRAY_SIZE = 200;
  function stackSet(key, value) {
    var data = this.__data__;
    if (data instanceof ListCache_default) {
      var pairs = data.__data__;
      if (!Map_default || pairs.length < LARGE_ARRAY_SIZE - 1) {
        pairs.push([key, value]);
        this.size = ++data.size;
        return this;
      }
      data = this.__data__ = new MapCache_default(pairs);
    }
    data.set(key, value);
    this.size = data.size;
    return this;
  }
  var stackSet_default = stackSet;

  // node_modules/lodash-es/_Stack.js
  function Stack(entries) {
    var data = this.__data__ = new ListCache_default(entries);
    this.size = data.size;
  }
  Stack.prototype.clear = stackClear_default;
  Stack.prototype["delete"] = stackDelete_default;
  Stack.prototype.get = stackGet_default;
  Stack.prototype.has = stackHas_default;
  Stack.prototype.set = stackSet_default;
  var Stack_default = Stack;

  // node_modules/lodash-es/_baseAssign.js
  function baseAssign(object, source) {
    return object && copyObject_default(source, keys_default(source), object);
  }
  var baseAssign_default = baseAssign;

  // node_modules/lodash-es/_baseAssignIn.js
  function baseAssignIn(object, source) {
    return object && copyObject_default(source, keysIn_default(source), object);
  }
  var baseAssignIn_default = baseAssignIn;

  // node_modules/lodash-es/_cloneBuffer.js
  var freeExports3 = typeof exports == "object" && exports && !exports.nodeType && exports;
  var freeModule3 = freeExports3 && typeof module == "object" && module && !module.nodeType && module;
  var moduleExports3 = freeModule3 && freeModule3.exports === freeExports3;
  var Buffer3 = moduleExports3 ? root_default.Buffer : void 0;
  var allocUnsafe = Buffer3 ? Buffer3.allocUnsafe : void 0;
  function cloneBuffer(buffer, isDeep) {
    if (isDeep) {
      return buffer.slice();
    }
    var length = buffer.length, result = allocUnsafe ? allocUnsafe(length) : new buffer.constructor(length);
    buffer.copy(result);
    return result;
  }
  var cloneBuffer_default = cloneBuffer;

  // node_modules/lodash-es/_arrayFilter.js
  function arrayFilter(array, predicate) {
    var index = -1, length = array == null ? 0 : array.length, resIndex = 0, result = [];
    while (++index < length) {
      var value = array[index];
      if (predicate(value, index, array)) {
        result[resIndex++] = value;
      }
    }
    return result;
  }
  var arrayFilter_default = arrayFilter;

  // node_modules/lodash-es/stubArray.js
  function stubArray() {
    return [];
  }
  var stubArray_default = stubArray;

  // node_modules/lodash-es/_getSymbols.js
  var objectProto13 = Object.prototype;
  var propertyIsEnumerable2 = objectProto13.propertyIsEnumerable;
  var nativeGetSymbols = Object.getOwnPropertySymbols;
  var getSymbols = !nativeGetSymbols ? stubArray_default : function(object) {
    if (object == null) {
      return [];
    }
    object = Object(object);
    return arrayFilter_default(nativeGetSymbols(object), function(symbol) {
      return propertyIsEnumerable2.call(object, symbol);
    });
  };
  var getSymbols_default = getSymbols;

  // node_modules/lodash-es/_copySymbols.js
  function copySymbols(source, object) {
    return copyObject_default(source, getSymbols_default(source), object);
  }
  var copySymbols_default = copySymbols;

  // node_modules/lodash-es/_getSymbolsIn.js
  var nativeGetSymbols2 = Object.getOwnPropertySymbols;
  var getSymbolsIn = !nativeGetSymbols2 ? stubArray_default : function(object) {
    var result = [];
    while (object) {
      arrayPush_default(result, getSymbols_default(object));
      object = getPrototype_default(object);
    }
    return result;
  };
  var getSymbolsIn_default = getSymbolsIn;

  // node_modules/lodash-es/_copySymbolsIn.js
  function copySymbolsIn(source, object) {
    return copyObject_default(source, getSymbolsIn_default(source), object);
  }
  var copySymbolsIn_default = copySymbolsIn;

  // node_modules/lodash-es/_baseGetAllKeys.js
  function baseGetAllKeys(object, keysFunc, symbolsFunc) {
    var result = keysFunc(object);
    return isArray_default(object) ? result : arrayPush_default(result, symbolsFunc(object));
  }
  var baseGetAllKeys_default = baseGetAllKeys;

  // node_modules/lodash-es/_getAllKeys.js
  function getAllKeys(object) {
    return baseGetAllKeys_default(object, keys_default, getSymbols_default);
  }
  var getAllKeys_default = getAllKeys;

  // node_modules/lodash-es/_getAllKeysIn.js
  function getAllKeysIn(object) {
    return baseGetAllKeys_default(object, keysIn_default, getSymbolsIn_default);
  }
  var getAllKeysIn_default = getAllKeysIn;

  // node_modules/lodash-es/_DataView.js
  var DataView = getNative_default(root_default, "DataView");
  var DataView_default = DataView;

  // node_modules/lodash-es/_Promise.js
  var Promise2 = getNative_default(root_default, "Promise");
  var Promise_default = Promise2;

  // node_modules/lodash-es/_Set.js
  var Set = getNative_default(root_default, "Set");
  var Set_default = Set;

  // node_modules/lodash-es/_getTag.js
  var mapTag2 = "[object Map]";
  var objectTag3 = "[object Object]";
  var promiseTag = "[object Promise]";
  var setTag2 = "[object Set]";
  var weakMapTag2 = "[object WeakMap]";
  var dataViewTag2 = "[object DataView]";
  var dataViewCtorString = toSource_default(DataView_default);
  var mapCtorString = toSource_default(Map_default);
  var promiseCtorString = toSource_default(Promise_default);
  var setCtorString = toSource_default(Set_default);
  var weakMapCtorString = toSource_default(WeakMap_default);
  var getTag = baseGetTag_default;
  if (DataView_default && getTag(new DataView_default(new ArrayBuffer(1))) != dataViewTag2 || Map_default && getTag(new Map_default()) != mapTag2 || Promise_default && getTag(Promise_default.resolve()) != promiseTag || Set_default && getTag(new Set_default()) != setTag2 || WeakMap_default && getTag(new WeakMap_default()) != weakMapTag2) {
    getTag = function(value) {
      var result = baseGetTag_default(value), Ctor = result == objectTag3 ? value.constructor : void 0, ctorString = Ctor ? toSource_default(Ctor) : "";
      if (ctorString) {
        switch (ctorString) {
          case dataViewCtorString:
            return dataViewTag2;
          case mapCtorString:
            return mapTag2;
          case promiseCtorString:
            return promiseTag;
          case setCtorString:
            return setTag2;
          case weakMapCtorString:
            return weakMapTag2;
        }
      }
      return result;
    };
  }
  var getTag_default = getTag;

  // node_modules/lodash-es/_initCloneArray.js
  var objectProto14 = Object.prototype;
  var hasOwnProperty11 = objectProto14.hasOwnProperty;
  function initCloneArray(array) {
    var length = array.length, result = new array.constructor(length);
    if (length && typeof array[0] == "string" && hasOwnProperty11.call(array, "index")) {
      result.index = array.index;
      result.input = array.input;
    }
    return result;
  }
  var initCloneArray_default = initCloneArray;

  // node_modules/lodash-es/_Uint8Array.js
  var Uint8Array2 = root_default.Uint8Array;
  var Uint8Array_default = Uint8Array2;

  // node_modules/lodash-es/_cloneArrayBuffer.js
  function cloneArrayBuffer(arrayBuffer) {
    var result = new arrayBuffer.constructor(arrayBuffer.byteLength);
    new Uint8Array_default(result).set(new Uint8Array_default(arrayBuffer));
    return result;
  }
  var cloneArrayBuffer_default = cloneArrayBuffer;

  // node_modules/lodash-es/_cloneDataView.js
  function cloneDataView(dataView, isDeep) {
    var buffer = isDeep ? cloneArrayBuffer_default(dataView.buffer) : dataView.buffer;
    return new dataView.constructor(buffer, dataView.byteOffset, dataView.byteLength);
  }
  var cloneDataView_default = cloneDataView;

  // node_modules/lodash-es/_cloneRegExp.js
  var reFlags = /\w*$/;
  function cloneRegExp(regexp) {
    var result = new regexp.constructor(regexp.source, reFlags.exec(regexp));
    result.lastIndex = regexp.lastIndex;
    return result;
  }
  var cloneRegExp_default = cloneRegExp;

  // node_modules/lodash-es/_cloneSymbol.js
  var symbolProto2 = Symbol_default ? Symbol_default.prototype : void 0;
  var symbolValueOf = symbolProto2 ? symbolProto2.valueOf : void 0;
  function cloneSymbol(symbol) {
    return symbolValueOf ? Object(symbolValueOf.call(symbol)) : {};
  }
  var cloneSymbol_default = cloneSymbol;

  // node_modules/lodash-es/_cloneTypedArray.js
  function cloneTypedArray(typedArray, isDeep) {
    var buffer = isDeep ? cloneArrayBuffer_default(typedArray.buffer) : typedArray.buffer;
    return new typedArray.constructor(buffer, typedArray.byteOffset, typedArray.length);
  }
  var cloneTypedArray_default = cloneTypedArray;

  // node_modules/lodash-es/_initCloneByTag.js
  var boolTag2 = "[object Boolean]";
  var dateTag2 = "[object Date]";
  var mapTag3 = "[object Map]";
  var numberTag2 = "[object Number]";
  var regexpTag2 = "[object RegExp]";
  var setTag3 = "[object Set]";
  var stringTag2 = "[object String]";
  var symbolTag2 = "[object Symbol]";
  var arrayBufferTag2 = "[object ArrayBuffer]";
  var dataViewTag3 = "[object DataView]";
  var float32Tag2 = "[object Float32Array]";
  var float64Tag2 = "[object Float64Array]";
  var int8Tag2 = "[object Int8Array]";
  var int16Tag2 = "[object Int16Array]";
  var int32Tag2 = "[object Int32Array]";
  var uint8Tag2 = "[object Uint8Array]";
  var uint8ClampedTag2 = "[object Uint8ClampedArray]";
  var uint16Tag2 = "[object Uint16Array]";
  var uint32Tag2 = "[object Uint32Array]";
  function initCloneByTag(object, tag, isDeep) {
    var Ctor = object.constructor;
    switch (tag) {
      case arrayBufferTag2:
        return cloneArrayBuffer_default(object);
      case boolTag2:
      case dateTag2:
        return new Ctor(+object);
      case dataViewTag3:
        return cloneDataView_default(object, isDeep);
      case float32Tag2:
      case float64Tag2:
      case int8Tag2:
      case int16Tag2:
      case int32Tag2:
      case uint8Tag2:
      case uint8ClampedTag2:
      case uint16Tag2:
      case uint32Tag2:
        return cloneTypedArray_default(object, isDeep);
      case mapTag3:
        return new Ctor();
      case numberTag2:
      case stringTag2:
        return new Ctor(object);
      case regexpTag2:
        return cloneRegExp_default(object);
      case setTag3:
        return new Ctor();
      case symbolTag2:
        return cloneSymbol_default(object);
    }
  }
  var initCloneByTag_default = initCloneByTag;

  // node_modules/lodash-es/_initCloneObject.js
  function initCloneObject(object) {
    return typeof object.constructor == "function" && !isPrototype_default(object) ? baseCreate_default(getPrototype_default(object)) : {};
  }
  var initCloneObject_default = initCloneObject;

  // node_modules/lodash-es/_baseIsMap.js
  var mapTag4 = "[object Map]";
  function baseIsMap(value) {
    return isObjectLike_default(value) && getTag_default(value) == mapTag4;
  }
  var baseIsMap_default = baseIsMap;

  // node_modules/lodash-es/isMap.js
  var nodeIsMap = nodeUtil_default && nodeUtil_default.isMap;
  var isMap = nodeIsMap ? baseUnary_default(nodeIsMap) : baseIsMap_default;
  var isMap_default = isMap;

  // node_modules/lodash-es/_baseIsSet.js
  var setTag4 = "[object Set]";
  function baseIsSet(value) {
    return isObjectLike_default(value) && getTag_default(value) == setTag4;
  }
  var baseIsSet_default = baseIsSet;

  // node_modules/lodash-es/isSet.js
  var nodeIsSet = nodeUtil_default && nodeUtil_default.isSet;
  var isSet = nodeIsSet ? baseUnary_default(nodeIsSet) : baseIsSet_default;
  var isSet_default = isSet;

  // node_modules/lodash-es/_baseClone.js
  var CLONE_DEEP_FLAG = 1;
  var CLONE_FLAT_FLAG = 2;
  var CLONE_SYMBOLS_FLAG = 4;
  var argsTag3 = "[object Arguments]";
  var arrayTag2 = "[object Array]";
  var boolTag3 = "[object Boolean]";
  var dateTag3 = "[object Date]";
  var errorTag2 = "[object Error]";
  var funcTag3 = "[object Function]";
  var genTag2 = "[object GeneratorFunction]";
  var mapTag5 = "[object Map]";
  var numberTag3 = "[object Number]";
  var objectTag4 = "[object Object]";
  var regexpTag3 = "[object RegExp]";
  var setTag5 = "[object Set]";
  var stringTag3 = "[object String]";
  var symbolTag3 = "[object Symbol]";
  var weakMapTag3 = "[object WeakMap]";
  var arrayBufferTag3 = "[object ArrayBuffer]";
  var dataViewTag4 = "[object DataView]";
  var float32Tag3 = "[object Float32Array]";
  var float64Tag3 = "[object Float64Array]";
  var int8Tag3 = "[object Int8Array]";
  var int16Tag3 = "[object Int16Array]";
  var int32Tag3 = "[object Int32Array]";
  var uint8Tag3 = "[object Uint8Array]";
  var uint8ClampedTag3 = "[object Uint8ClampedArray]";
  var uint16Tag3 = "[object Uint16Array]";
  var uint32Tag3 = "[object Uint32Array]";
  var cloneableTags = {};
  cloneableTags[argsTag3] = cloneableTags[arrayTag2] = cloneableTags[arrayBufferTag3] = cloneableTags[dataViewTag4] = cloneableTags[boolTag3] = cloneableTags[dateTag3] = cloneableTags[float32Tag3] = cloneableTags[float64Tag3] = cloneableTags[int8Tag3] = cloneableTags[int16Tag3] = cloneableTags[int32Tag3] = cloneableTags[mapTag5] = cloneableTags[numberTag3] = cloneableTags[objectTag4] = cloneableTags[regexpTag3] = cloneableTags[setTag5] = cloneableTags[stringTag3] = cloneableTags[symbolTag3] = cloneableTags[uint8Tag3] = cloneableTags[uint8ClampedTag3] = cloneableTags[uint16Tag3] = cloneableTags[uint32Tag3] = true;
  cloneableTags[errorTag2] = cloneableTags[funcTag3] = cloneableTags[weakMapTag3] = false;
  function baseClone(value, bitmask, customizer, key, object, stack) {
    var result, isDeep = bitmask & CLONE_DEEP_FLAG, isFlat = bitmask & CLONE_FLAT_FLAG, isFull = bitmask & CLONE_SYMBOLS_FLAG;
    if (customizer) {
      result = object ? customizer(value, key, object, stack) : customizer(value);
    }
    if (result !== void 0) {
      return result;
    }
    if (!isObject_default(value)) {
      return value;
    }
    var isArr = isArray_default(value);
    if (isArr) {
      result = initCloneArray_default(value);
      if (!isDeep) {
        return copyArray_default(value, result);
      }
    } else {
      var tag = getTag_default(value), isFunc = tag == funcTag3 || tag == genTag2;
      if (isBuffer_default(value)) {
        return cloneBuffer_default(value, isDeep);
      }
      if (tag == objectTag4 || tag == argsTag3 || isFunc && !object) {
        result = isFlat || isFunc ? {} : initCloneObject_default(value);
        if (!isDeep) {
          return isFlat ? copySymbolsIn_default(value, baseAssignIn_default(result, value)) : copySymbols_default(value, baseAssign_default(result, value));
        }
      } else {
        if (!cloneableTags[tag]) {
          return object ? value : {};
        }
        result = initCloneByTag_default(value, tag, isDeep);
      }
    }
    stack || (stack = new Stack_default());
    var stacked = stack.get(value);
    if (stacked) {
      return stacked;
    }
    stack.set(value, result);
    if (isSet_default(value)) {
      value.forEach(function(subValue) {
        result.add(baseClone(subValue, bitmask, customizer, subValue, value, stack));
      });
    } else if (isMap_default(value)) {
      value.forEach(function(subValue, key2) {
        result.set(key2, baseClone(subValue, bitmask, customizer, key2, value, stack));
      });
    }
    var keysFunc = isFull ? isFlat ? getAllKeysIn_default : getAllKeys_default : isFlat ? keysIn_default : keys_default;
    var props = isArr ? void 0 : keysFunc(value);
    arrayEach_default(props || value, function(subValue, key2) {
      if (props) {
        key2 = subValue;
        subValue = value[key2];
      }
      assignValue_default(result, key2, baseClone(subValue, bitmask, customizer, key2, value, stack));
    });
    return result;
  }
  var baseClone_default = baseClone;

  // node_modules/lodash-es/cloneDeep.js
  var CLONE_DEEP_FLAG2 = 1;
  var CLONE_SYMBOLS_FLAG2 = 4;
  function cloneDeep(value) {
    return baseClone_default(value, CLONE_DEEP_FLAG2 | CLONE_SYMBOLS_FLAG2);
  }
  var cloneDeep_default = cloneDeep;

  // node_modules/lodash-es/_setCacheAdd.js
  var HASH_UNDEFINED3 = "__lodash_hash_undefined__";
  function setCacheAdd(value) {
    this.__data__.set(value, HASH_UNDEFINED3);
    return this;
  }
  var setCacheAdd_default = setCacheAdd;

  // node_modules/lodash-es/_setCacheHas.js
  function setCacheHas(value) {
    return this.__data__.has(value);
  }
  var setCacheHas_default = setCacheHas;

  // node_modules/lodash-es/_SetCache.js
  function SetCache(values2) {
    var index = -1, length = values2 == null ? 0 : values2.length;
    this.__data__ = new MapCache_default();
    while (++index < length) {
      this.add(values2[index]);
    }
  }
  SetCache.prototype.add = SetCache.prototype.push = setCacheAdd_default;
  SetCache.prototype.has = setCacheHas_default;
  var SetCache_default = SetCache;

  // node_modules/lodash-es/_arraySome.js
  function arraySome(array, predicate) {
    var index = -1, length = array == null ? 0 : array.length;
    while (++index < length) {
      if (predicate(array[index], index, array)) {
        return true;
      }
    }
    return false;
  }
  var arraySome_default = arraySome;

  // node_modules/lodash-es/_cacheHas.js
  function cacheHas(cache, key) {
    return cache.has(key);
  }
  var cacheHas_default = cacheHas;

  // node_modules/lodash-es/_equalArrays.js
  var COMPARE_PARTIAL_FLAG = 1;
  var COMPARE_UNORDERED_FLAG = 2;
  function equalArrays(array, other, bitmask, customizer, equalFunc, stack) {
    var isPartial = bitmask & COMPARE_PARTIAL_FLAG, arrLength = array.length, othLength = other.length;
    if (arrLength != othLength && !(isPartial && othLength > arrLength)) {
      return false;
    }
    var arrStacked = stack.get(array);
    var othStacked = stack.get(other);
    if (arrStacked && othStacked) {
      return arrStacked == other && othStacked == array;
    }
    var index = -1, result = true, seen = bitmask & COMPARE_UNORDERED_FLAG ? new SetCache_default() : void 0;
    stack.set(array, other);
    stack.set(other, array);
    while (++index < arrLength) {
      var arrValue = array[index], othValue = other[index];
      if (customizer) {
        var compared = isPartial ? customizer(othValue, arrValue, index, other, array, stack) : customizer(arrValue, othValue, index, array, other, stack);
      }
      if (compared !== void 0) {
        if (compared) {
          continue;
        }
        result = false;
        break;
      }
      if (seen) {
        if (!arraySome_default(other, function(othValue2, othIndex) {
          if (!cacheHas_default(seen, othIndex) && (arrValue === othValue2 || equalFunc(arrValue, othValue2, bitmask, customizer, stack))) {
            return seen.push(othIndex);
          }
        })) {
          result = false;
          break;
        }
      } else if (!(arrValue === othValue || equalFunc(arrValue, othValue, bitmask, customizer, stack))) {
        result = false;
        break;
      }
    }
    stack["delete"](array);
    stack["delete"](other);
    return result;
  }
  var equalArrays_default = equalArrays;

  // node_modules/lodash-es/_mapToArray.js
  function mapToArray(map2) {
    var index = -1, result = Array(map2.size);
    map2.forEach(function(value, key) {
      result[++index] = [key, value];
    });
    return result;
  }
  var mapToArray_default = mapToArray;

  // node_modules/lodash-es/_setToArray.js
  function setToArray(set) {
    var index = -1, result = Array(set.size);
    set.forEach(function(value) {
      result[++index] = value;
    });
    return result;
  }
  var setToArray_default = setToArray;

  // node_modules/lodash-es/_equalByTag.js
  var COMPARE_PARTIAL_FLAG2 = 1;
  var COMPARE_UNORDERED_FLAG2 = 2;
  var boolTag4 = "[object Boolean]";
  var dateTag4 = "[object Date]";
  var errorTag3 = "[object Error]";
  var mapTag6 = "[object Map]";
  var numberTag4 = "[object Number]";
  var regexpTag4 = "[object RegExp]";
  var setTag6 = "[object Set]";
  var stringTag4 = "[object String]";
  var symbolTag4 = "[object Symbol]";
  var arrayBufferTag4 = "[object ArrayBuffer]";
  var dataViewTag5 = "[object DataView]";
  var symbolProto3 = Symbol_default ? Symbol_default.prototype : void 0;
  var symbolValueOf2 = symbolProto3 ? symbolProto3.valueOf : void 0;
  function equalByTag(object, other, tag, bitmask, customizer, equalFunc, stack) {
    switch (tag) {
      case dataViewTag5:
        if (object.byteLength != other.byteLength || object.byteOffset != other.byteOffset) {
          return false;
        }
        object = object.buffer;
        other = other.buffer;
      case arrayBufferTag4:
        if (object.byteLength != other.byteLength || !equalFunc(new Uint8Array_default(object), new Uint8Array_default(other))) {
          return false;
        }
        return true;
      case boolTag4:
      case dateTag4:
      case numberTag4:
        return eq_default(+object, +other);
      case errorTag3:
        return object.name == other.name && object.message == other.message;
      case regexpTag4:
      case stringTag4:
        return object == other + "";
      case mapTag6:
        var convert = mapToArray_default;
      case setTag6:
        var isPartial = bitmask & COMPARE_PARTIAL_FLAG2;
        convert || (convert = setToArray_default);
        if (object.size != other.size && !isPartial) {
          return false;
        }
        var stacked = stack.get(object);
        if (stacked) {
          return stacked == other;
        }
        bitmask |= COMPARE_UNORDERED_FLAG2;
        stack.set(object, other);
        var result = equalArrays_default(convert(object), convert(other), bitmask, customizer, equalFunc, stack);
        stack["delete"](object);
        return result;
      case symbolTag4:
        if (symbolValueOf2) {
          return symbolValueOf2.call(object) == symbolValueOf2.call(other);
        }
    }
    return false;
  }
  var equalByTag_default = equalByTag;

  // node_modules/lodash-es/_equalObjects.js
  var COMPARE_PARTIAL_FLAG3 = 1;
  var objectProto15 = Object.prototype;
  var hasOwnProperty12 = objectProto15.hasOwnProperty;
  function equalObjects(object, other, bitmask, customizer, equalFunc, stack) {
    var isPartial = bitmask & COMPARE_PARTIAL_FLAG3, objProps = getAllKeys_default(object), objLength = objProps.length, othProps = getAllKeys_default(other), othLength = othProps.length;
    if (objLength != othLength && !isPartial) {
      return false;
    }
    var index = objLength;
    while (index--) {
      var key = objProps[index];
      if (!(isPartial ? key in other : hasOwnProperty12.call(other, key))) {
        return false;
      }
    }
    var objStacked = stack.get(object);
    var othStacked = stack.get(other);
    if (objStacked && othStacked) {
      return objStacked == other && othStacked == object;
    }
    var result = true;
    stack.set(object, other);
    stack.set(other, object);
    var skipCtor = isPartial;
    while (++index < objLength) {
      key = objProps[index];
      var objValue = object[key], othValue = other[key];
      if (customizer) {
        var compared = isPartial ? customizer(othValue, objValue, key, other, object, stack) : customizer(objValue, othValue, key, object, other, stack);
      }
      if (!(compared === void 0 ? objValue === othValue || equalFunc(objValue, othValue, bitmask, customizer, stack) : compared)) {
        result = false;
        break;
      }
      skipCtor || (skipCtor = key == "constructor");
    }
    if (result && !skipCtor) {
      var objCtor = object.constructor, othCtor = other.constructor;
      if (objCtor != othCtor && ("constructor" in object && "constructor" in other) && !(typeof objCtor == "function" && objCtor instanceof objCtor && typeof othCtor == "function" && othCtor instanceof othCtor)) {
        result = false;
      }
    }
    stack["delete"](object);
    stack["delete"](other);
    return result;
  }
  var equalObjects_default = equalObjects;

  // node_modules/lodash-es/_baseIsEqualDeep.js
  var COMPARE_PARTIAL_FLAG4 = 1;
  var argsTag4 = "[object Arguments]";
  var arrayTag3 = "[object Array]";
  var objectTag5 = "[object Object]";
  var objectProto16 = Object.prototype;
  var hasOwnProperty13 = objectProto16.hasOwnProperty;
  function baseIsEqualDeep(object, other, bitmask, customizer, equalFunc, stack) {
    var objIsArr = isArray_default(object), othIsArr = isArray_default(other), objTag = objIsArr ? arrayTag3 : getTag_default(object), othTag = othIsArr ? arrayTag3 : getTag_default(other);
    objTag = objTag == argsTag4 ? objectTag5 : objTag;
    othTag = othTag == argsTag4 ? objectTag5 : othTag;
    var objIsObj = objTag == objectTag5, othIsObj = othTag == objectTag5, isSameTag = objTag == othTag;
    if (isSameTag && isBuffer_default(object)) {
      if (!isBuffer_default(other)) {
        return false;
      }
      objIsArr = true;
      objIsObj = false;
    }
    if (isSameTag && !objIsObj) {
      stack || (stack = new Stack_default());
      return objIsArr || isTypedArray_default(object) ? equalArrays_default(object, other, bitmask, customizer, equalFunc, stack) : equalByTag_default(object, other, objTag, bitmask, customizer, equalFunc, stack);
    }
    if (!(bitmask & COMPARE_PARTIAL_FLAG4)) {
      var objIsWrapped = objIsObj && hasOwnProperty13.call(object, "__wrapped__"), othIsWrapped = othIsObj && hasOwnProperty13.call(other, "__wrapped__");
      if (objIsWrapped || othIsWrapped) {
        var objUnwrapped = objIsWrapped ? object.value() : object, othUnwrapped = othIsWrapped ? other.value() : other;
        stack || (stack = new Stack_default());
        return equalFunc(objUnwrapped, othUnwrapped, bitmask, customizer, stack);
      }
    }
    if (!isSameTag) {
      return false;
    }
    stack || (stack = new Stack_default());
    return equalObjects_default(object, other, bitmask, customizer, equalFunc, stack);
  }
  var baseIsEqualDeep_default = baseIsEqualDeep;

  // node_modules/lodash-es/_baseIsEqual.js
  function baseIsEqual(value, other, bitmask, customizer, stack) {
    if (value === other) {
      return true;
    }
    if (value == null || other == null || !isObjectLike_default(value) && !isObjectLike_default(other)) {
      return value !== value && other !== other;
    }
    return baseIsEqualDeep_default(value, other, bitmask, customizer, baseIsEqual, stack);
  }
  var baseIsEqual_default = baseIsEqual;

  // node_modules/lodash-es/_baseIsMatch.js
  var COMPARE_PARTIAL_FLAG5 = 1;
  var COMPARE_UNORDERED_FLAG3 = 2;
  function baseIsMatch(object, source, matchData, customizer) {
    var index = matchData.length, length = index, noCustomizer = !customizer;
    if (object == null) {
      return !length;
    }
    object = Object(object);
    while (index--) {
      var data = matchData[index];
      if (noCustomizer && data[2] ? data[1] !== object[data[0]] : !(data[0] in object)) {
        return false;
      }
    }
    while (++index < length) {
      data = matchData[index];
      var key = data[0], objValue = object[key], srcValue = data[1];
      if (noCustomizer && data[2]) {
        if (objValue === void 0 && !(key in object)) {
          return false;
        }
      } else {
        var stack = new Stack_default();
        if (customizer) {
          var result = customizer(objValue, srcValue, key, object, source, stack);
        }
        if (!(result === void 0 ? baseIsEqual_default(srcValue, objValue, COMPARE_PARTIAL_FLAG5 | COMPARE_UNORDERED_FLAG3, customizer, stack) : result)) {
          return false;
        }
      }
    }
    return true;
  }
  var baseIsMatch_default = baseIsMatch;

  // node_modules/lodash-es/_isStrictComparable.js
  function isStrictComparable(value) {
    return value === value && !isObject_default(value);
  }
  var isStrictComparable_default = isStrictComparable;

  // node_modules/lodash-es/_getMatchData.js
  function getMatchData(object) {
    var result = keys_default(object), length = result.length;
    while (length--) {
      var key = result[length], value = object[key];
      result[length] = [key, value, isStrictComparable_default(value)];
    }
    return result;
  }
  var getMatchData_default = getMatchData;

  // node_modules/lodash-es/_matchesStrictComparable.js
  function matchesStrictComparable(key, srcValue) {
    return function(object) {
      if (object == null) {
        return false;
      }
      return object[key] === srcValue && (srcValue !== void 0 || key in Object(object));
    };
  }
  var matchesStrictComparable_default = matchesStrictComparable;

  // node_modules/lodash-es/_baseMatches.js
  function baseMatches(source) {
    var matchData = getMatchData_default(source);
    if (matchData.length == 1 && matchData[0][2]) {
      return matchesStrictComparable_default(matchData[0][0], matchData[0][1]);
    }
    return function(object) {
      return object === source || baseIsMatch_default(object, source, matchData);
    };
  }
  var baseMatches_default = baseMatches;

  // node_modules/lodash-es/_baseHasIn.js
  function baseHasIn(object, key) {
    return object != null && key in Object(object);
  }
  var baseHasIn_default = baseHasIn;

  // node_modules/lodash-es/_hasPath.js
  function hasPath(object, path, hasFunc) {
    path = castPath_default(path, object);
    var index = -1, length = path.length, result = false;
    while (++index < length) {
      var key = toKey_default(path[index]);
      if (!(result = object != null && hasFunc(object, key))) {
        break;
      }
      object = object[key];
    }
    if (result || ++index != length) {
      return result;
    }
    length = object == null ? 0 : object.length;
    return !!length && isLength_default(length) && isIndex_default(key, length) && (isArray_default(object) || isArguments_default(object));
  }
  var hasPath_default = hasPath;

  // node_modules/lodash-es/hasIn.js
  function hasIn(object, path) {
    return object != null && hasPath_default(object, path, baseHasIn_default);
  }
  var hasIn_default = hasIn;

  // node_modules/lodash-es/_baseMatchesProperty.js
  var COMPARE_PARTIAL_FLAG6 = 1;
  var COMPARE_UNORDERED_FLAG4 = 2;
  function baseMatchesProperty(path, srcValue) {
    if (isKey_default(path) && isStrictComparable_default(srcValue)) {
      return matchesStrictComparable_default(toKey_default(path), srcValue);
    }
    return function(object) {
      var objValue = get_default(object, path);
      return objValue === void 0 && objValue === srcValue ? hasIn_default(object, path) : baseIsEqual_default(srcValue, objValue, COMPARE_PARTIAL_FLAG6 | COMPARE_UNORDERED_FLAG4);
    };
  }
  var baseMatchesProperty_default = baseMatchesProperty;

  // node_modules/lodash-es/_baseProperty.js
  function baseProperty(key) {
    return function(object) {
      return object == null ? void 0 : object[key];
    };
  }
  var baseProperty_default = baseProperty;

  // node_modules/lodash-es/_basePropertyDeep.js
  function basePropertyDeep(path) {
    return function(object) {
      return baseGet_default(object, path);
    };
  }
  var basePropertyDeep_default = basePropertyDeep;

  // node_modules/lodash-es/property.js
  function property(path) {
    return isKey_default(path) ? baseProperty_default(toKey_default(path)) : basePropertyDeep_default(path);
  }
  var property_default = property;

  // node_modules/lodash-es/_baseIteratee.js
  function baseIteratee(value) {
    if (typeof value == "function") {
      return value;
    }
    if (value == null) {
      return identity_default;
    }
    if (typeof value == "object") {
      return isArray_default(value) ? baseMatchesProperty_default(value[0], value[1]) : baseMatches_default(value);
    }
    return property_default(value);
  }
  var baseIteratee_default = baseIteratee;

  // node_modules/lodash-es/_createBaseFor.js
  function createBaseFor(fromRight) {
    return function(object, iteratee, keysFunc) {
      var index = -1, iterable = Object(object), props = keysFunc(object), length = props.length;
      while (length--) {
        var key = props[fromRight ? length : ++index];
        if (iteratee(iterable[key], key, iterable) === false) {
          break;
        }
      }
      return object;
    };
  }
  var createBaseFor_default = createBaseFor;

  // node_modules/lodash-es/_baseFor.js
  var baseFor = createBaseFor_default();
  var baseFor_default = baseFor;

  // node_modules/lodash-es/_baseForOwn.js
  function baseForOwn(object, iteratee) {
    return object && baseFor_default(object, iteratee, keys_default);
  }
  var baseForOwn_default = baseForOwn;

  // node_modules/lodash-es/_createBaseEach.js
  function createBaseEach(eachFunc, fromRight) {
    return function(collection, iteratee) {
      if (collection == null) {
        return collection;
      }
      if (!isArrayLike_default(collection)) {
        return eachFunc(collection, iteratee);
      }
      var length = collection.length, index = fromRight ? length : -1, iterable = Object(collection);
      while (fromRight ? index-- : ++index < length) {
        if (iteratee(iterable[index], index, iterable) === false) {
          break;
        }
      }
      return collection;
    };
  }
  var createBaseEach_default = createBaseEach;

  // node_modules/lodash-es/_baseEach.js
  var baseEach = createBaseEach_default(baseForOwn_default);
  var baseEach_default = baseEach;

  // node_modules/lodash-es/now.js
  var now = function() {
    return root_default.Date.now();
  };
  var now_default = now;

  // node_modules/lodash-es/defaults.js
  var objectProto17 = Object.prototype;
  var hasOwnProperty14 = objectProto17.hasOwnProperty;
  var defaults = baseRest_default(function(object, sources) {
    object = Object(object);
    var index = -1;
    var length = sources.length;
    var guard = length > 2 ? sources[2] : void 0;
    if (guard && isIterateeCall_default(sources[0], sources[1], guard)) {
      length = 1;
    }
    while (++index < length) {
      var source = sources[index];
      var props = keysIn_default(source);
      var propsIndex = -1;
      var propsLength = props.length;
      while (++propsIndex < propsLength) {
        var key = props[propsIndex];
        var value = object[key];
        if (value === void 0 || eq_default(value, objectProto17[key]) && !hasOwnProperty14.call(object, key)) {
          object[key] = source[key];
        }
      }
    }
    return object;
  });
  var defaults_default = defaults;

  // node_modules/lodash-es/_assignMergeValue.js
  function assignMergeValue(object, key, value) {
    if (value !== void 0 && !eq_default(object[key], value) || value === void 0 && !(key in object)) {
      baseAssignValue_default(object, key, value);
    }
  }
  var assignMergeValue_default = assignMergeValue;

  // node_modules/lodash-es/isArrayLikeObject.js
  function isArrayLikeObject(value) {
    return isObjectLike_default(value) && isArrayLike_default(value);
  }
  var isArrayLikeObject_default = isArrayLikeObject;

  // node_modules/lodash-es/_safeGet.js
  function safeGet(object, key) {
    if (key === "constructor" && typeof object[key] === "function") {
      return;
    }
    if (key == "__proto__") {
      return;
    }
    return object[key];
  }
  var safeGet_default = safeGet;

  // node_modules/lodash-es/toPlainObject.js
  function toPlainObject(value) {
    return copyObject_default(value, keysIn_default(value));
  }
  var toPlainObject_default = toPlainObject;

  // node_modules/lodash-es/_baseMergeDeep.js
  function baseMergeDeep(object, source, key, srcIndex, mergeFunc, customizer, stack) {
    var objValue = safeGet_default(object, key), srcValue = safeGet_default(source, key), stacked = stack.get(srcValue);
    if (stacked) {
      assignMergeValue_default(object, key, stacked);
      return;
    }
    var newValue = customizer ? customizer(objValue, srcValue, key + "", object, source, stack) : void 0;
    var isCommon = newValue === void 0;
    if (isCommon) {
      var isArr = isArray_default(srcValue), isBuff = !isArr && isBuffer_default(srcValue), isTyped = !isArr && !isBuff && isTypedArray_default(srcValue);
      newValue = srcValue;
      if (isArr || isBuff || isTyped) {
        if (isArray_default(objValue)) {
          newValue = objValue;
        } else if (isArrayLikeObject_default(objValue)) {
          newValue = copyArray_default(objValue);
        } else if (isBuff) {
          isCommon = false;
          newValue = cloneBuffer_default(srcValue, true);
        } else if (isTyped) {
          isCommon = false;
          newValue = cloneTypedArray_default(srcValue, true);
        } else {
          newValue = [];
        }
      } else if (isPlainObject_default(srcValue) || isArguments_default(srcValue)) {
        newValue = objValue;
        if (isArguments_default(objValue)) {
          newValue = toPlainObject_default(objValue);
        } else if (!isObject_default(objValue) || isFunction_default(objValue)) {
          newValue = initCloneObject_default(srcValue);
        }
      } else {
        isCommon = false;
      }
    }
    if (isCommon) {
      stack.set(srcValue, newValue);
      mergeFunc(newValue, srcValue, srcIndex, customizer, stack);
      stack["delete"](srcValue);
    }
    assignMergeValue_default(object, key, newValue);
  }
  var baseMergeDeep_default = baseMergeDeep;

  // node_modules/lodash-es/_baseMerge.js
  function baseMerge(object, source, srcIndex, customizer, stack) {
    if (object === source) {
      return;
    }
    baseFor_default(source, function(srcValue, key) {
      stack || (stack = new Stack_default());
      if (isObject_default(srcValue)) {
        baseMergeDeep_default(object, source, key, srcIndex, baseMerge, customizer, stack);
      } else {
        var newValue = customizer ? customizer(safeGet_default(object, key), srcValue, key + "", object, source, stack) : void 0;
        if (newValue === void 0) {
          newValue = srcValue;
        }
        assignMergeValue_default(object, key, newValue);
      }
    }, keysIn_default);
  }
  var baseMerge_default = baseMerge;

  // node_modules/lodash-es/_arrayIncludesWith.js
  function arrayIncludesWith(array, value, comparator) {
    var index = -1, length = array == null ? 0 : array.length;
    while (++index < length) {
      if (comparator(value, array[index])) {
        return true;
      }
    }
    return false;
  }
  var arrayIncludesWith_default = arrayIncludesWith;

  // node_modules/lodash-es/last.js
  function last(array) {
    var length = array == null ? 0 : array.length;
    return length ? array[length - 1] : void 0;
  }
  var last_default = last;

  // node_modules/lodash-es/_castFunction.js
  function castFunction(value) {
    return typeof value == "function" ? value : identity_default;
  }
  var castFunction_default = castFunction;

  // node_modules/lodash-es/forEach.js
  function forEach(collection, iteratee) {
    var func = isArray_default(collection) ? arrayEach_default : baseEach_default;
    return func(collection, castFunction_default(iteratee));
  }
  var forEach_default = forEach;

  // node_modules/lodash-es/_baseFilter.js
  function baseFilter(collection, predicate) {
    var result = [];
    baseEach_default(collection, function(value, index, collection2) {
      if (predicate(value, index, collection2)) {
        result.push(value);
      }
    });
    return result;
  }
  var baseFilter_default = baseFilter;

  // node_modules/lodash-es/filter.js
  function filter(collection, predicate) {
    var func = isArray_default(collection) ? arrayFilter_default : baseFilter_default;
    return func(collection, baseIteratee_default(predicate, 3));
  }
  var filter_default = filter;

  // node_modules/lodash-es/_createFind.js
  function createFind(findIndexFunc) {
    return function(collection, predicate, fromIndex) {
      var iterable = Object(collection);
      if (!isArrayLike_default(collection)) {
        var iteratee = baseIteratee_default(predicate, 3);
        collection = keys_default(collection);
        predicate = function(key) {
          return iteratee(iterable[key], key, iterable);
        };
      }
      var index = findIndexFunc(collection, predicate, fromIndex);
      return index > -1 ? iterable[iteratee ? collection[index] : index] : void 0;
    };
  }
  var createFind_default = createFind;

  // node_modules/lodash-es/findIndex.js
  var nativeMax2 = Math.max;
  function findIndex(array, predicate, fromIndex) {
    var length = array == null ? 0 : array.length;
    if (!length) {
      return -1;
    }
    var index = fromIndex == null ? 0 : toInteger_default(fromIndex);
    if (index < 0) {
      index = nativeMax2(length + index, 0);
    }
    return baseFindIndex_default(array, baseIteratee_default(predicate, 3), index);
  }
  var findIndex_default = findIndex;

  // node_modules/lodash-es/find.js
  var find = createFind_default(findIndex_default);
  var find_default = find;

  // node_modules/lodash-es/_baseMap.js
  function baseMap(collection, iteratee) {
    var index = -1, result = isArrayLike_default(collection) ? Array(collection.length) : [];
    baseEach_default(collection, function(value, key, collection2) {
      result[++index] = iteratee(value, key, collection2);
    });
    return result;
  }
  var baseMap_default = baseMap;

  // node_modules/lodash-es/map.js
  function map(collection, iteratee) {
    var func = isArray_default(collection) ? arrayMap_default : baseMap_default;
    return func(collection, baseIteratee_default(iteratee, 3));
  }
  var map_default = map;

  // node_modules/lodash-es/forIn.js
  function forIn(object, iteratee) {
    return object == null ? object : baseFor_default(object, castFunction_default(iteratee), keysIn_default);
  }
  var forIn_default = forIn;

  // node_modules/lodash-es/forOwn.js
  function forOwn(object, iteratee) {
    return object && baseForOwn_default(object, castFunction_default(iteratee));
  }
  var forOwn_default = forOwn;

  // node_modules/lodash-es/_baseGt.js
  function baseGt(value, other) {
    return value > other;
  }
  var baseGt_default = baseGt;

  // node_modules/lodash-es/_baseHas.js
  var objectProto18 = Object.prototype;
  var hasOwnProperty15 = objectProto18.hasOwnProperty;
  function baseHas(object, key) {
    return object != null && hasOwnProperty15.call(object, key);
  }
  var baseHas_default = baseHas;

  // node_modules/lodash-es/has.js
  function has(object, path) {
    return object != null && hasPath_default(object, path, baseHas_default);
  }
  var has_default = has;

  // node_modules/lodash-es/isString.js
  var stringTag5 = "[object String]";
  function isString(value) {
    return typeof value == "string" || !isArray_default(value) && isObjectLike_default(value) && baseGetTag_default(value) == stringTag5;
  }
  var isString_default = isString;

  // node_modules/lodash-es/_baseValues.js
  function baseValues(object, props) {
    return arrayMap_default(props, function(key) {
      return object[key];
    });
  }
  var baseValues_default = baseValues;

  // node_modules/lodash-es/values.js
  function values(object) {
    return object == null ? [] : baseValues_default(object, keys_default(object));
  }
  var values_default = values;

  // node_modules/lodash-es/isEmpty.js
  var mapTag7 = "[object Map]";
  var setTag7 = "[object Set]";
  var objectProto19 = Object.prototype;
  var hasOwnProperty16 = objectProto19.hasOwnProperty;
  function isEmpty(value) {
    if (value == null) {
      return true;
    }
    if (isArrayLike_default(value) && (isArray_default(value) || typeof value == "string" || typeof value.splice == "function" || isBuffer_default(value) || isTypedArray_default(value) || isArguments_default(value))) {
      return !value.length;
    }
    var tag = getTag_default(value);
    if (tag == mapTag7 || tag == setTag7) {
      return !value.size;
    }
    if (isPrototype_default(value)) {
      return !baseKeys_default(value).length;
    }
    for (var key in value) {
      if (hasOwnProperty16.call(value, key)) {
        return false;
      }
    }
    return true;
  }
  var isEmpty_default = isEmpty;

  // node_modules/lodash-es/isUndefined.js
  function isUndefined(value) {
    return value === void 0;
  }
  var isUndefined_default = isUndefined;

  // node_modules/lodash-es/_baseLt.js
  function baseLt(value, other) {
    return value < other;
  }
  var baseLt_default = baseLt;

  // node_modules/lodash-es/mapValues.js
  function mapValues(object, iteratee) {
    var result = {};
    iteratee = baseIteratee_default(iteratee, 3);
    baseForOwn_default(object, function(value, key, object2) {
      baseAssignValue_default(result, key, iteratee(value, key, object2));
    });
    return result;
  }
  var mapValues_default = mapValues;

  // node_modules/lodash-es/_baseExtremum.js
  function baseExtremum(array, iteratee, comparator) {
    var index = -1, length = array.length;
    while (++index < length) {
      var value = array[index], current = iteratee(value);
      if (current != null && (computed === void 0 ? current === current && !isSymbol_default(current) : comparator(current, computed))) {
        var computed = current, result = value;
      }
    }
    return result;
  }
  var baseExtremum_default = baseExtremum;

  // node_modules/lodash-es/max.js
  function max(array) {
    return array && array.length ? baseExtremum_default(array, identity_default, baseGt_default) : void 0;
  }
  var max_default = max;

  // node_modules/lodash-es/merge.js
  var merge = createAssigner_default(function(object, source, srcIndex) {
    baseMerge_default(object, source, srcIndex);
  });
  var merge_default = merge;

  // node_modules/lodash-es/min.js
  function min(array) {
    return array && array.length ? baseExtremum_default(array, identity_default, baseLt_default) : void 0;
  }
  var min_default = min;

  // node_modules/lodash-es/minBy.js
  function minBy(array, iteratee) {
    return array && array.length ? baseExtremum_default(array, baseIteratee_default(iteratee, 2), baseLt_default) : void 0;
  }
  var minBy_default = minBy;

  // node_modules/lodash-es/_baseSet.js
  function baseSet(object, path, value, customizer) {
    if (!isObject_default(object)) {
      return object;
    }
    path = castPath_default(path, object);
    var index = -1, length = path.length, lastIndex = length - 1, nested = object;
    while (nested != null && ++index < length) {
      var key = toKey_default(path[index]), newValue = value;
      if (key === "__proto__" || key === "constructor" || key === "prototype") {
        return object;
      }
      if (index != lastIndex) {
        var objValue = nested[key];
        newValue = customizer ? customizer(objValue, key, nested) : void 0;
        if (newValue === void 0) {
          newValue = isObject_default(objValue) ? objValue : isIndex_default(path[index + 1]) ? [] : {};
        }
      }
      assignValue_default(nested, key, newValue);
      nested = nested[key];
    }
    return object;
  }
  var baseSet_default = baseSet;

  // node_modules/lodash-es/_basePickBy.js
  function basePickBy(object, paths, predicate) {
    var index = -1, length = paths.length, result = {};
    while (++index < length) {
      var path = paths[index], value = baseGet_default(object, path);
      if (predicate(value, path)) {
        baseSet_default(result, castPath_default(path, object), value);
      }
    }
    return result;
  }
  var basePickBy_default = basePickBy;

  // node_modules/lodash-es/_baseSortBy.js
  function baseSortBy(array, comparer) {
    var length = array.length;
    array.sort(comparer);
    while (length--) {
      array[length] = array[length].value;
    }
    return array;
  }
  var baseSortBy_default = baseSortBy;

  // node_modules/lodash-es/_compareAscending.js
  function compareAscending(value, other) {
    if (value !== other) {
      var valIsDefined = value !== void 0, valIsNull = value === null, valIsReflexive = value === value, valIsSymbol = isSymbol_default(value);
      var othIsDefined = other !== void 0, othIsNull = other === null, othIsReflexive = other === other, othIsSymbol = isSymbol_default(other);
      if (!othIsNull && !othIsSymbol && !valIsSymbol && value > other || valIsSymbol && othIsDefined && othIsReflexive && !othIsNull && !othIsSymbol || valIsNull && othIsDefined && othIsReflexive || !valIsDefined && othIsReflexive || !valIsReflexive) {
        return 1;
      }
      if (!valIsNull && !valIsSymbol && !othIsSymbol && value < other || othIsSymbol && valIsDefined && valIsReflexive && !valIsNull && !valIsSymbol || othIsNull && valIsDefined && valIsReflexive || !othIsDefined && valIsReflexive || !othIsReflexive) {
        return -1;
      }
    }
    return 0;
  }
  var compareAscending_default = compareAscending;

  // node_modules/lodash-es/_compareMultiple.js
  function compareMultiple(object, other, orders) {
    var index = -1, objCriteria = object.criteria, othCriteria = other.criteria, length = objCriteria.length, ordersLength = orders.length;
    while (++index < length) {
      var result = compareAscending_default(objCriteria[index], othCriteria[index]);
      if (result) {
        if (index >= ordersLength) {
          return result;
        }
        var order2 = orders[index];
        return result * (order2 == "desc" ? -1 : 1);
      }
    }
    return object.index - other.index;
  }
  var compareMultiple_default = compareMultiple;

  // node_modules/lodash-es/_baseOrderBy.js
  function baseOrderBy(collection, iteratees, orders) {
    if (iteratees.length) {
      iteratees = arrayMap_default(iteratees, function(iteratee) {
        if (isArray_default(iteratee)) {
          return function(value) {
            return baseGet_default(value, iteratee.length === 1 ? iteratee[0] : iteratee);
          };
        }
        return iteratee;
      });
    } else {
      iteratees = [identity_default];
    }
    var index = -1;
    iteratees = arrayMap_default(iteratees, baseUnary_default(baseIteratee_default));
    var result = baseMap_default(collection, function(value, key, collection2) {
      var criteria = arrayMap_default(iteratees, function(iteratee) {
        return iteratee(value);
      });
      return { "criteria": criteria, "index": ++index, "value": value };
    });
    return baseSortBy_default(result, function(object, other) {
      return compareMultiple_default(object, other, orders);
    });
  }
  var baseOrderBy_default = baseOrderBy;

  // node_modules/lodash-es/_asciiSize.js
  var asciiSize = baseProperty_default("length");
  var asciiSize_default = asciiSize;

  // node_modules/lodash-es/_unicodeSize.js
  var rsAstralRange2 = "\\ud800-\\udfff";
  var rsComboMarksRange2 = "\\u0300-\\u036f";
  var reComboHalfMarksRange2 = "\\ufe20-\\ufe2f";
  var rsComboSymbolsRange2 = "\\u20d0-\\u20ff";
  var rsComboRange2 = rsComboMarksRange2 + reComboHalfMarksRange2 + rsComboSymbolsRange2;
  var rsVarRange2 = "\\ufe0e\\ufe0f";
  var rsAstral = "[" + rsAstralRange2 + "]";
  var rsCombo = "[" + rsComboRange2 + "]";
  var rsFitz = "\\ud83c[\\udffb-\\udfff]";
  var rsModifier = "(?:" + rsCombo + "|" + rsFitz + ")";
  var rsNonAstral = "[^" + rsAstralRange2 + "]";
  var rsRegional = "(?:\\ud83c[\\udde6-\\uddff]){2}";
  var rsSurrPair = "[\\ud800-\\udbff][\\udc00-\\udfff]";
  var rsZWJ2 = "\\u200d";
  var reOptMod = rsModifier + "?";
  var rsOptVar = "[" + rsVarRange2 + "]?";
  var rsOptJoin = "(?:" + rsZWJ2 + "(?:" + [rsNonAstral, rsRegional, rsSurrPair].join("|") + ")" + rsOptVar + reOptMod + ")*";
  var rsSeq = rsOptVar + reOptMod + rsOptJoin;
  var rsSymbol = "(?:" + [rsNonAstral + rsCombo + "?", rsCombo, rsRegional, rsSurrPair, rsAstral].join("|") + ")";
  var reUnicode = RegExp(rsFitz + "(?=" + rsFitz + ")|" + rsSymbol + rsSeq, "g");
  function unicodeSize(string) {
    var result = reUnicode.lastIndex = 0;
    while (reUnicode.test(string)) {
      ++result;
    }
    return result;
  }
  var unicodeSize_default = unicodeSize;

  // node_modules/lodash-es/_stringSize.js
  function stringSize(string) {
    return hasUnicode_default(string) ? unicodeSize_default(string) : asciiSize_default(string);
  }
  var stringSize_default = stringSize;

  // node_modules/lodash-es/_basePick.js
  function basePick(object, paths) {
    return basePickBy_default(object, paths, function(value, path) {
      return hasIn_default(object, path);
    });
  }
  var basePick_default = basePick;

  // node_modules/lodash-es/pick.js
  var pick = flatRest_default(function(object, paths) {
    return object == null ? {} : basePick_default(object, paths);
  });
  var pick_default = pick;

  // node_modules/lodash-es/_baseRange.js
  var nativeCeil = Math.ceil;
  var nativeMax3 = Math.max;
  function baseRange(start, end, step, fromRight) {
    var index = -1, length = nativeMax3(nativeCeil((end - start) / (step || 1)), 0), result = Array(length);
    while (length--) {
      result[fromRight ? length : ++index] = start;
      start += step;
    }
    return result;
  }
  var baseRange_default = baseRange;

  // node_modules/lodash-es/_createRange.js
  function createRange(fromRight) {
    return function(start, end, step) {
      if (step && typeof step != "number" && isIterateeCall_default(start, end, step)) {
        end = step = void 0;
      }
      start = toFinite_default(start);
      if (end === void 0) {
        end = start;
        start = 0;
      } else {
        end = toFinite_default(end);
      }
      step = step === void 0 ? start < end ? 1 : -1 : toFinite_default(step);
      return baseRange_default(start, end, step, fromRight);
    };
  }
  var createRange_default = createRange;

  // node_modules/lodash-es/range.js
  var range = createRange_default();
  var range_default = range;

  // node_modules/lodash-es/_baseReduce.js
  function baseReduce(collection, iteratee, accumulator, initAccum, eachFunc) {
    eachFunc(collection, function(value, index, collection2) {
      accumulator = initAccum ? (initAccum = false, value) : iteratee(accumulator, value, index, collection2);
    });
    return accumulator;
  }
  var baseReduce_default = baseReduce;

  // node_modules/lodash-es/reduce.js
  function reduce(collection, iteratee, accumulator) {
    var func = isArray_default(collection) ? arrayReduce_default : baseReduce_default, initAccum = arguments.length < 3;
    return func(collection, baseIteratee_default(iteratee, 4), accumulator, initAccum, baseEach_default);
  }
  var reduce_default = reduce;

  // node_modules/lodash-es/size.js
  var mapTag8 = "[object Map]";
  var setTag8 = "[object Set]";
  function size(collection) {
    if (collection == null) {
      return 0;
    }
    if (isArrayLike_default(collection)) {
      return isString_default(collection) ? stringSize_default(collection) : collection.length;
    }
    var tag = getTag_default(collection);
    if (tag == mapTag8 || tag == setTag8) {
      return collection.size;
    }
    return baseKeys_default(collection).length;
  }
  var size_default = size;

  // node_modules/lodash-es/sortBy.js
  var sortBy = baseRest_default(function(collection, iteratees) {
    if (collection == null) {
      return [];
    }
    var length = iteratees.length;
    if (length > 1 && isIterateeCall_default(collection, iteratees[0], iteratees[1])) {
      iteratees = [];
    } else if (length > 2 && isIterateeCall_default(iteratees[0], iteratees[1], iteratees[2])) {
      iteratees = [iteratees[0]];
    }
    return baseOrderBy_default(collection, baseFlatten_default(iteratees, 1), []);
  });
  var sortBy_default = sortBy;

  // node_modules/lodash-es/_createSet.js
  var INFINITY4 = 1 / 0;
  var createSet = !(Set_default && 1 / setToArray_default(new Set_default([, -0]))[1] == INFINITY4) ? noop_default : function(values2) {
    return new Set_default(values2);
  };
  var createSet_default = createSet;

  // node_modules/lodash-es/_baseUniq.js
  var LARGE_ARRAY_SIZE2 = 200;
  function baseUniq(array, iteratee, comparator) {
    var index = -1, includes = arrayIncludes_default, length = array.length, isCommon = true, result = [], seen = result;
    if (comparator) {
      isCommon = false;
      includes = arrayIncludesWith_default;
    } else if (length >= LARGE_ARRAY_SIZE2) {
      var set = iteratee ? null : createSet_default(array);
      if (set) {
        return setToArray_default(set);
      }
      isCommon = false;
      includes = cacheHas_default;
      seen = new SetCache_default();
    } else {
      seen = iteratee ? [] : result;
    }
    outer:
      while (++index < length) {
        var value = array[index], computed = iteratee ? iteratee(value) : value;
        value = comparator || value !== 0 ? value : 0;
        if (isCommon && computed === computed) {
          var seenIndex = seen.length;
          while (seenIndex--) {
            if (seen[seenIndex] === computed) {
              continue outer;
            }
          }
          if (iteratee) {
            seen.push(computed);
          }
          result.push(value);
        } else if (!includes(seen, computed, comparator)) {
          if (seen !== result) {
            seen.push(computed);
          }
          result.push(value);
        }
      }
    return result;
  }
  var baseUniq_default = baseUniq;

  // node_modules/lodash-es/union.js
  var union = baseRest_default(function(arrays) {
    return baseUniq_default(baseFlatten_default(arrays, 1, isArrayLikeObject_default, true));
  });
  var union_default = union;

  // node_modules/lodash-es/uniqueId.js
  var idCounter = 0;
  function uniqueId(prefix) {
    var id = ++idCounter;
    return toString_default(prefix) + id;
  }
  var uniqueId_default = uniqueId;

  // node_modules/lodash-es/_baseZipObject.js
  function baseZipObject(props, values2, assignFunc) {
    var index = -1, length = props.length, valsLength = values2.length, result = {};
    while (++index < length) {
      var value = index < valsLength ? values2[index] : void 0;
      assignFunc(result, props[index], value);
    }
    return result;
  }
  var baseZipObject_default = baseZipObject;

  // node_modules/lodash-es/zipObject.js
  function zipObject(props, values2) {
    return baseZipObject_default(props || [], values2 || [], assignValue_default);
  }
  var zipObject_default = zipObject;

  // node_modules/dagre-d3-es/src/graphlib/index.js
  var graphlib_exports = {};
  __export(graphlib_exports, {
    Graph: () => Graph,
    version: () => version
  });

  // node_modules/dagre-d3-es/src/graphlib/graph.js
  var DEFAULT_EDGE_NAME = "\0";
  var GRAPH_NODE = "\0";
  var EDGE_KEY_DELIM = "";
  var Graph = class {
    /**
     * @param {GraphOptions} [opts] - Graph options.
     */
    constructor(opts = {}) {
      this._isDirected = Object.prototype.hasOwnProperty.call(opts, "directed") ? opts.directed : true;
      this._isMultigraph = Object.prototype.hasOwnProperty.call(opts, "multigraph") ? opts.multigraph : false;
      this._isCompound = Object.prototype.hasOwnProperty.call(opts, "compound") ? opts.compound : false;
      this._label = void 0;
      this._defaultNodeLabelFn = constant_default(void 0);
      this._defaultEdgeLabelFn = constant_default(void 0);
      this._nodes = {};
      if (this._isCompound) {
        this._parent = {};
        this._children = {};
        this._children[GRAPH_NODE] = {};
      }
      this._in = {};
      this._preds = {};
      this._out = {};
      this._sucs = {};
      this._edgeObjs = {};
      this._edgeLabels = {};
    }
    /* === Graph functions ========= */
    /**
     *
     * @returns {boolean} `true` if the graph is [directed](https://en.wikipedia.org/wiki/Directed_graph).
     * A directed graph treats the order of nodes in an edge as significant whereas an
     * [undirected](https://en.wikipedia.org/wiki/Graph_(mathematics)#Undirected_graph)
     * graph does not.
     * This example demonstrates the difference:
     *
     * @example
     *
     * ```js
     * var directed = new Graph({ directed: true });
     * directed.setEdge("a", "b", "my-label");
     * directed.edge("a", "b"); // returns "my-label"
     * directed.edge("b", "a"); // returns undefined
     *
     * var undirected = new Graph({ directed: false });
     * undirected.setEdge("a", "b", "my-label");
     * undirected.edge("a", "b"); // returns "my-label"
     * undirected.edge("b", "a"); // returns "my-label"
     * ```
     */
    isDirected() {
      return this._isDirected;
    }
    /**
     * @returns {boolean} `true` if the graph is a multigraph.
     */
    isMultigraph() {
      return this._isMultigraph;
    }
    /**
     * @returns {boolean} `true` if the graph is compound.
     */
    isCompound() {
      return this._isCompound;
    }
    /**
     * Sets the label for the graph to `label`.
     *
     * @param {GraphLabel} label - Label for the graph.
     * @returns {this}
     */
    setGraph(label) {
      this._label = label;
      return this;
    }
    /**
     * @returns {GraphLabel | undefined} the currently assigned label for the graph.
     * If no label has been assigned, returns `undefined`.
     *
     * @example
     *
     * ```js
     * var g = new Graph();
     * g.graph(); // returns undefined
     * g.setGraph("graph-label");
     *  g.graph(); // returns "graph-label"
     * ```
     */
    graph() {
      return this._label;
    }
    /* === Node functions ========== */
    /**
     * Sets a new default value that is assigned to nodes that are created without
     * a label.
     *
     * @param {typeof this._defaultNodeLabelFn | NodeLabel} newDefault - If a function,
     * it is called with the id of the node being created.
     * Otherwise, it is assigned as the label directly.
     * @returns {this}
     */
    setDefaultNodeLabel(newDefault) {
      if (!isFunction_default(newDefault)) {
        newDefault = constant_default(newDefault);
      }
      this._defaultNodeLabelFn = newDefault;
      return this;
    }
    /**
     * @returns {number} the number of nodes in the graph.
     */
    nodeCount() {
      return this._nodeCount;
    }
    /**
     * @returns {NodeID[]} the ids of the nodes in the graph.
     *
     * @remarks
     * Use {@link node()} to get the label for each node.
     * Takes `O(|V|)` time.
     */
    nodes() {
      return keys_default(this._nodes);
    }
    /**
     * @returns {NodeID[]} those nodes in the graph that have no in-edges.
     * @remarks Takes `O(|V|)` time.
     */
    sources() {
      var self2 = this;
      return filter_default(this.nodes(), function(v) {
        return isEmpty_default(self2._in[v]);
      });
    }
    /**
     * @returns {NodeID[]} those nodes in the graph that have no out-edges.
     * @remarks Takes `O(|V|)` time.
     */
    sinks() {
      var self2 = this;
      return filter_default(this.nodes(), function(v) {
        return isEmpty_default(self2._out[v]);
      });
    }
    /**
     * Invokes setNode method for each node in `vs` list.
     *
     * @param {Collection<NodeID | number>} vs - List of node IDs to create/set.
     * @param {NodeLabel} [value] - If set, update all nodes with this value.
     * @returns {this}
     * @remarks Complexity: O(|names|).
     */
    setNodes(vs, value) {
      var args = arguments;
      var self2 = this;
      forEach_default(vs, function(v) {
        if (args.length > 1) {
          self2.setNode(v, value);
        } else {
          self2.setNode(v);
        }
      });
      return this;
    }
    /**
     * Creates or updates the value for the node `v` in the graph.
     *
     * @param {NodeID | number} v - ID of the node to create/set.
     * @param {NodeLabel} [value] - If supplied, it is set as the value for the node.
     * If not supplied and the node was created by this call then
     * {@link setDefaultNodeLabel} will be used to set the node's value.
     * @returns {this} the graph, allowing this to be chained with other functions.
     * @remarks Takes `O(1)` time.
     */
    setNode(v, value) {
      if (Object.prototype.hasOwnProperty.call(this._nodes, v)) {
        if (arguments.length > 1) {
          this._nodes[v] = value;
        }
        return this;
      }
      this._nodes[v] = arguments.length > 1 ? value : this._defaultNodeLabelFn(v);
      if (this._isCompound) {
        this._parent[v] = GRAPH_NODE;
        this._children[v] = {};
        this._children[GRAPH_NODE][v] = true;
      }
      this._in[v] = {};
      this._preds[v] = {};
      this._out[v] = {};
      this._sucs[v] = {};
      ++this._nodeCount;
      return this;
    }
    /**
     * Gets the label of node with specified name.
     *
     * @param {NodeID | number} v - Node ID.
     * @returns {NodeLabel | undefined} the label assigned to the node with the id `v`
     * if it is in the graph.
     * Otherwise returns `undefined`.
     * @remarks Takes `O(1)` time.
     */
    node(v) {
      return this._nodes[v];
    }
    /**
     * Detects whether graph has a node with specified name or not.
     *
     * @param {NodeID | number} v - Node ID.
     * @returns {boolean} Returns `true` the graph has a node with the id.
     * @remarks Takes `O(1)` time.
     */
    hasNode(v) {
      return Object.prototype.hasOwnProperty.call(this._nodes, v);
    }
    /**
     * Remove the node with the id `v` in the graph or do nothing if the node is
     * not in the graph.
     *
     * If the node was removed this function also removes any incident edges.
     *
     * @param {NodeID | number} v - Node ID to remove.
     * @returns {this} the graph, allowing this to be chained with other functions.
     * @remarks Takes `O(|E|)` time.
     */
    removeNode(v) {
      if (Object.prototype.hasOwnProperty.call(this._nodes, v)) {
        var removeEdge = (e) => this.removeEdge(this._edgeObjs[e]);
        delete this._nodes[v];
        if (this._isCompound) {
          this._removeFromParentsChildList(v);
          delete this._parent[v];
          forEach_default(this.children(v), (child) => {
            this.setParent(child);
          });
          delete this._children[v];
        }
        forEach_default(keys_default(this._in[v]), removeEdge);
        delete this._in[v];
        delete this._preds[v];
        forEach_default(keys_default(this._out[v]), removeEdge);
        delete this._out[v];
        delete this._sucs[v];
        --this._nodeCount;
      }
      return this;
    }
    /**
     * Sets the parent for `v` to `parent` if it is defined or removes the parent
     * for `v` if `parent` is undefined.
     *
     * @param {NodeID | number} v - Node ID to set the parent for.
     * @param {NodeID | number} [parent] - Parent node ID. If not defined, removes the parent.
     * @returns {this} the graph, allowing this to be chained with other functions.
     * @throws if the graph is not compound.
     * @throws if setting the parent would create a cycle.
     * @remarks Takes `O(1)` time.
     */
    setParent(v, parent) {
      if (!this._isCompound) {
        throw new Error("Cannot set parent in a non-compound graph");
      }
      if (isUndefined_default(parent)) {
        parent = GRAPH_NODE;
      } else {
        parent += "";
        for (var ancestor = parent; !isUndefined_default(ancestor); ancestor = this.parent(ancestor)) {
          if (ancestor === v) {
            throw new Error("Setting " + parent + " as parent of " + v + " would create a cycle");
          }
        }
        this.setNode(parent);
      }
      this.setNode(v);
      this._removeFromParentsChildList(v);
      this._parent[v] = parent;
      this._children[parent][v] = true;
      return this;
    }
    /**
     * @private
     * @param {NodeID | number} v - Node ID.
     */
    _removeFromParentsChildList(v) {
      delete this._children[this._parent[v]][v];
    }
    /**
     * Get parent node for node `v`.
     *
     * @param {NodeID | number} v - Node ID.
     * @returns {NodeID | undefined} the node that is a parent of node `v`
     * or `undefined` if node `v` does not have a parent or is not a member of
     * the graph.
     * Always returns `undefined` for graphs that are not compound.
     * @remarks Takes `O(1)` time.
     */
    parent(v) {
      if (this._isCompound) {
        var parent = this._parent[v];
        if (parent !== GRAPH_NODE) {
          return parent;
        }
      }
    }
    /**
     * Gets list of direct children of node v.
     *
     * @param {NodeID | number} [v] - Node ID. If not specified, gets nodes
     * with no parent (top-level nodes).
     * @returns {NodeID[] | undefined} all nodes that are children of node `v` or
     * `undefined` if node `v` is not in the graph.
     * Always returns `[]` for graphs that are not compound.
     * @remarks Takes `O(|V|)` time.
     */
    children(v) {
      if (isUndefined_default(v)) {
        v = GRAPH_NODE;
      }
      if (this._isCompound) {
        var children = this._children[v];
        if (children) {
          return keys_default(children);
        }
      } else if (v === GRAPH_NODE) {
        return this.nodes();
      } else if (this.hasNode(v)) {
        return [];
      }
    }
    /**
     * @param {NodeID | number} v - Node ID.
     * @returns {NodeID[] | undefined} all nodes that are predecessors of the
     * specified node or `undefined` if node `v` is not in the graph.
     * @remarks
     * Behavior is undefined for undirected graphs - use {@link neighbors} instead.
     * Takes `O(|V|)` time.
     */
    predecessors(v) {
      var predsV = this._preds[v];
      if (predsV) {
        return keys_default(predsV);
      }
    }
    /**
     * @param {NodeID | number} v - Node ID.
     * @returns {NodeID[] | undefined} all nodes that are successors of the
     * specified node or `undefined` if node `v` is not in the graph.
     * @remarks
     * Behavior is undefined for undirected graphs - use {@link neighbors} instead.
     * Takes `O(|V|)` time.
     */
    successors(v) {
      var sucsV = this._sucs[v];
      if (sucsV) {
        return keys_default(sucsV);
      }
    }
    /**
     * @param {NodeID | number} v - Node ID.
     * @returns {NodeID[] | undefined} all nodes that are predecessors or
     * successors of the specified node
     * or `undefined` if node `v` is not in the graph.
     * @remarks Takes `O(|V|)` time.
     */
    neighbors(v) {
      var preds = this.predecessors(v);
      if (preds) {
        return union_default(preds, this.successors(v));
      }
    }
    /**
     * @param {NodeID | number} v - Node ID.
     * @returns {boolean} True if the node is a leaf (has no successors), false otherwise.
     */
    isLeaf(v) {
      var neighbors;
      if (this.isDirected()) {
        neighbors = this.successors(v);
      } else {
        neighbors = this.neighbors(v);
      }
      return neighbors.length === 0;
    }
    /**
       * Creates new graph with nodes filtered via `filter`.
       * Edges incident to rejected node
       * are also removed.
       * 
       * In case of compound graph, if parent is rejected by `filter`,
       * than all its children are rejected too.
    
       * @param {(v: NodeID) => boolean} filter - Function that returns `true` for nodes to keep.
       * @returns {Graph<GraphLabel, NodeLabel, EdgeLabel>} A new graph containing only the nodes for which `filter` returns `true`.
       * @remarks Average-case complexity: O(|E|+|V|).
       */
    filterNodes(filter2) {
      var copy = new this.constructor({
        directed: this._isDirected,
        multigraph: this._isMultigraph,
        compound: this._isCompound
      });
      copy.setGraph(this.graph());
      var self2 = this;
      forEach_default(this._nodes, function(value, v) {
        if (filter2(v)) {
          copy.setNode(v, value);
        }
      });
      forEach_default(this._edgeObjs, function(e) {
        if (copy.hasNode(e.v) && copy.hasNode(e.w)) {
          copy.setEdge(e, self2.edge(e));
        }
      });
      var parents = {};
      function findParent(v) {
        var parent = self2.parent(v);
        if (parent === void 0 || copy.hasNode(parent)) {
          parents[v] = parent;
          return parent;
        } else if (parent in parents) {
          return parents[parent];
        } else {
          return findParent(parent);
        }
      }
      if (this._isCompound) {
        forEach_default(copy.nodes(), function(v) {
          copy.setParent(v, findParent(v));
        });
      }
      return copy;
    }
    /* === Edge functions ========== */
    /**
     * Sets a new default value that is assigned to edges that are created without
     * a label.
     *
     * @param {typeof this._defaultEdgeLabelFn | EdgeLabel} newDefault - If a function,
     * it is called with the parameters `(v, w, name)`.
     * Otherwise, it is assigned as the label directly.
     * @returns {this}
     */
    setDefaultEdgeLabel(newDefault) {
      if (!isFunction_default(newDefault)) {
        newDefault = constant_default(newDefault);
      }
      this._defaultEdgeLabelFn = newDefault;
      return this;
    }
    /**
     * @returns {number} the number of edges in the graph.
     * @remarks Complexity: O(1).
     */
    edgeCount() {
      return this._edgeCount;
    }
    /**
     * Gets edges of the graph.
     *
     * @returns {EdgeObj[]} the {@link EdgeObj} for each edge in the graph.
     *
     * @remarks
     * In case of compound graph subgraphs are not considered.
     * Use {@link edge()} to get the label for each edge.
     * Takes `O(|E|)` time.
     */
    edges() {
      return values_default(this._edgeObjs);
    }
    /**
     * Establish an edges path over the nodes in nodes list.
     *
     * If some edge is already exists, it will update its label, otherwise it will
     * create an edge between pair of nodes with label provided or default label
     * if no label provided.
     *
     * @param {Collection<NodeID>} vs - List of node IDs to create edges between.
     * @param {EdgeLabel} [value] - If set, update all edges with this value.
     * @returns {this}
     * @remarks Complexity: O(|nodes|).
     */
    setPath(vs, value) {
      var self2 = this;
      var args = arguments;
      reduce_default(vs, function(v, w) {
        if (args.length > 1) {
          self2.setEdge(v, w, value);
        } else {
          self2.setEdge(v, w);
        }
        return w;
      });
      return this;
    }
    /**
     * Creates or updates the label for the edge (`v`, `w`) with the optionally
     * supplied `name`.
     *
     * @overload
     * @param {EdgeObj} arg0 - Edge object.
     * @param {EdgeLabel} [value] - If supplied, it is set as the label for the edge.
     * If not supplied and the edge was created by this call then
     * {@link setDefaultEdgeLabel} will be used to assign the edge's label.
     * @returns {this} the graph, allowing this to be chained with other functions.
     * @remarks Takes `O(1)` time.
     */
    /**
     * Creates or updates the label for the edge (`v`, `w`) with the optionally
     * supplied `name`.
     *
     * @overload
     * @param {NodeID | number} v - Source node ID. Number values will be coerced to strings.
     * @param {NodeID | number} w - Target node ID. Number values will be coerced to strings.
     * @param {EdgeLabel} [value] - If supplied, it is set as the label for the edge.
     * If not supplied and the edge was created by this call then
     * {@link setDefaultEdgeLabel} will be used to assign the edge's label.
     * @param {string | number} [name] - Edge name. Only useful with multigraphs.
     * @returns {this} the graph, allowing this to be chained with other functions.
     * @remarks Takes `O(1)` time.
     */
    setEdge() {
      var v, w, name, value;
      var valueSpecified = false;
      var arg0 = arguments[0];
      if (typeof arg0 === "object" && arg0 !== null && "v" in arg0) {
        v = arg0.v;
        w = arg0.w;
        name = arg0.name;
        if (arguments.length === 2) {
          value = arguments[1];
          valueSpecified = true;
        }
      } else {
        v = arg0;
        w = arguments[1];
        name = arguments[3];
        if (arguments.length > 2) {
          value = arguments[2];
          valueSpecified = true;
        }
      }
      v = "" + v;
      w = "" + w;
      if (!isUndefined_default(name)) {
        name = "" + name;
      }
      var e = edgeArgsToId(this._isDirected, v, w, name);
      if (Object.prototype.hasOwnProperty.call(this._edgeLabels, e)) {
        if (valueSpecified) {
          this._edgeLabels[e] = value;
        }
        return this;
      }
      if (!isUndefined_default(name) && !this._isMultigraph) {
        throw new Error("Cannot set a named edge when isMultigraph = false");
      }
      this.setNode(v);
      this.setNode(w);
      this._edgeLabels[e] = valueSpecified ? value : this._defaultEdgeLabelFn(v, w, name);
      var edgeObj = edgeArgsToObj(this._isDirected, v, w, name);
      v = edgeObj.v;
      w = edgeObj.w;
      Object.freeze(edgeObj);
      this._edgeObjs[e] = edgeObj;
      incrementOrInitEntry(this._preds[w], v);
      incrementOrInitEntry(this._sucs[v], w);
      this._in[w][e] = edgeObj;
      this._out[v][e] = edgeObj;
      this._edgeCount++;
      return this;
    }
    /**
     * Gets the label for the specified edge.
     *
     * @overload
     * @param {EdgeObj} v - Edge object.
     * @returns {EdgeLabel | undefined} the label for the edge (`v`, `w`) if the
     * graph has an edge between `v` and `w` with the optional `name`.
     * Returned `undefined` if there is no such edge in the graph.
     * @remarks
     * `v` and `w` can be interchanged for undirected graphs.
     * Takes `O(1)` time.
     */
    /**
     * Gets the label for the specified edge.
     *
     * @overload
     * @param {NodeID | number} v - Source node ID.
     * @param {NodeID | number} w - Target node ID.
     * @param {string | number} [name] - Edge name. Only useful with multigraphs.
     * @returns {EdgeLabel | undefined} the label for the edge (`v`, `w`) if the
     * graph has an edge between `v` and `w` with the optional `name`.
     * Returned `undefined` if there is no such edge in the graph.
     * @remarks
     * `v` and `w` can be interchanged for undirected graphs.
     * Takes `O(1)` time.
     */
    edge(v, w, name) {
      var e = arguments.length === 1 ? edgeObjToId(this._isDirected, arguments[0]) : edgeArgsToId(this._isDirected, v, w, name);
      return this._edgeLabels[e];
    }
    /**
     * Detects whether the graph contains specified edge or not.
     *
     * @overload
     * @param {EdgeObj} v - Edge object.
     * @returns {boolean} `true` if the graph has an edge between `v` and `w`
     * with the optional `name`.
     * @remarks
     * `v` and `w` can be interchanged for undirected graphs.
     * No subgraphs are considered.
     * Takes `O(1)` time.
     */
    /**
     * Detects whether the graph contains specified edge or not.
     *
     * @overload
     * @param {NodeID | number} v - Source node ID.
     * @param {NodeID | number} w - Target node ID.
     * @param {string | number} [name] - Edge name. Only useful with multigraphs.
     * @returns {boolean} `true` if the graph has an edge between `v` and `w`
     * with the optional `name`.
     * @remarks
     * `v` and `w` can be interchanged for undirected graphs.
     * No subgraphs are considered.
     * Takes `O(1)` time.
     */
    hasEdge(v, w, name) {
      var e = arguments.length === 1 ? edgeObjToId(this._isDirected, arguments[0]) : edgeArgsToId(this._isDirected, v, w, name);
      return Object.prototype.hasOwnProperty.call(this._edgeLabels, e);
    }
    /**
     * Removes the edge (`v`, `w`) if the graph has an edge between `v` and `w`
     * with the optional `name`. If not this function does nothing.
     *
     * @overload
     * @param {EdgeObj} v - Edge object.
     * @returns {this}
     * @remarks
     * `v` and `w` can be interchanged for undirected graphs.
     * No subgraphs are considered.
     * Takes `O(1)` time.
     */
    /**
     * Removes the edge (`v`, `w`) if the graph has an edge between `v` and `w`
     * with the optional `name`. If not this function does nothing.
     *
     * @overload
     * @param {NodeID | number} v - Source node ID.
     * @param {NodeID | number} w - Target node ID.
     * @param {string | number} [name] - Edge name. Only useful with multigraphs.
     * @returns {this}
     * @remarks
     * `v` and `w` can be interchanged for undirected graphs.
     * Takes `O(1)` time.
     */
    removeEdge(v, w, name) {
      var e = arguments.length === 1 ? edgeObjToId(this._isDirected, arguments[0]) : edgeArgsToId(this._isDirected, v, w, name);
      var edge = this._edgeObjs[e];
      if (edge) {
        v = edge.v;
        w = edge.w;
        delete this._edgeLabels[e];
        delete this._edgeObjs[e];
        decrementOrRemoveEntry(this._preds[w], v);
        decrementOrRemoveEntry(this._sucs[v], w);
        delete this._in[w][e];
        delete this._out[v][e];
        this._edgeCount--;
      }
      return this;
    }
    /**
     * @param {NodeID | number} v - Target node ID.
     * @param {NodeID | number} [u] - Optionally filters edges down to just those
     * coming from node `u`.
     * @returns {EdgeObj[] | undefined} all edges that point to the node `v`.
     * Returns `undefined` if node `v` is not in the graph.
     * @remarks
     * Behavior is undefined for undirected graphs - use {@link nodeEdges} instead.
     * Takes `O(|E|)` time.
     */
    inEdges(v, u) {
      var inV = this._in[v];
      if (inV) {
        var edges = values_default(inV);
        if (!u) {
          return edges;
        }
        return filter_default(edges, function(edge) {
          return edge.v === u;
        });
      }
    }
    /**
     * @param {NodeID | number} v - Target node ID.
     * @param {NodeID | number} [w] - Optionally filters edges down to just those
     * that point to `w`.
     * @returns {EdgeObj[] | undefined} all edges that point to the node `v`.
     * Returns `undefined` if node `v` is not in the graph.
     * @remarks
     * Behavior is undefined for undirected graphs - use {@link nodeEdges} instead.
     * Takes `O(|E|)` time.
     */
    outEdges(v, w) {
      var outV = this._out[v];
      if (outV) {
        var edges = values_default(outV);
        if (!w) {
          return edges;
        }
        return filter_default(edges, function(edge) {
          return edge.w === w;
        });
      }
    }
    /**
     * @param {NodeID | number} v - Target Node ID.
     * @param {NodeID | number} [w] - If set, filters those edges down to just
     * those between nodes `v` and `w` regardless of direction
     * @returns {EdgeObj[] | undefined} all edges to or from node `v` regardless
     * of direction. Returns `undefined` if node `v` is not in the graph.
     * @remarks Takes `O(|E|)` time.
     */
    nodeEdges(v, w) {
      var inEdges = this.inEdges(v, w);
      if (inEdges) {
        return inEdges.concat(this.outEdges(v, w));
      }
    }
  };
  Graph.prototype._nodeCount = 0;
  Graph.prototype._edgeCount = 0;
  function incrementOrInitEntry(map2, k) {
    if (map2[k]) {
      map2[k]++;
    } else {
      map2[k] = 1;
    }
  }
  function decrementOrRemoveEntry(map2, k) {
    if (!--map2[k]) {
      delete map2[k];
    }
  }
  function edgeArgsToId(isDirected, v_, w_, name) {
    var v = "" + v_;
    var w = "" + w_;
    if (!isDirected && v > w) {
      var tmp = v;
      v = w;
      w = tmp;
    }
    return v + EDGE_KEY_DELIM + w + EDGE_KEY_DELIM + (isUndefined_default(name) ? DEFAULT_EDGE_NAME : name);
  }
  function edgeArgsToObj(isDirected, v_, w_, name) {
    var v = "" + v_;
    var w = "" + w_;
    if (!isDirected && v > w) {
      var tmp = v;
      v = w;
      w = tmp;
    }
    var edgeObj = { v, w };
    if (name) {
      edgeObj.name = name;
    }
    return edgeObj;
  }
  function edgeObjToId(isDirected, edgeObj) {
    return edgeArgsToId(isDirected, edgeObj.v, edgeObj.w, edgeObj.name);
  }

  // node_modules/dagre-d3-es/src/graphlib/index.js
  var version = "2.1.9-pre";

  // node_modules/dagre-d3-es/src/dagre/data/list.js
  var List = class {
    constructor() {
      var sentinel = {};
      sentinel._next = sentinel._prev = sentinel;
      this._sentinel = sentinel;
    }
    dequeue() {
      var sentinel = this._sentinel;
      var entry = sentinel._prev;
      if (entry !== sentinel) {
        unlink(entry);
        return entry;
      }
    }
    enqueue(entry) {
      var sentinel = this._sentinel;
      if (entry._prev && entry._next) {
        unlink(entry);
      }
      entry._next = sentinel._next;
      sentinel._next._prev = entry;
      sentinel._next = entry;
      entry._prev = sentinel;
    }
    toString() {
      var strs = [];
      var sentinel = this._sentinel;
      var curr = sentinel._prev;
      while (curr !== sentinel) {
        strs.push(JSON.stringify(curr, filterOutLinks));
        curr = curr._prev;
      }
      return "[" + strs.join(", ") + "]";
    }
  };
  function unlink(entry) {
    entry._prev._next = entry._next;
    entry._next._prev = entry._prev;
    delete entry._next;
    delete entry._prev;
  }
  function filterOutLinks(k, v) {
    if (k !== "_next" && k !== "_prev") {
      return v;
    }
  }

  // node_modules/dagre-d3-es/src/dagre/greedy-fas.js
  var DEFAULT_WEIGHT_FN = constant_default(1);
  function greedyFAS(g, weightFn) {
    if (g.nodeCount() <= 1) {
      return [];
    }
    var state = buildState(g, weightFn || DEFAULT_WEIGHT_FN);
    var results = doGreedyFAS(state.graph, state.buckets, state.zeroIdx);
    return flatten_default(
      map_default(results, function(e) {
        return g.outEdges(e.v, e.w);
      })
    );
  }
  function doGreedyFAS(g, buckets, zeroIdx) {
    var results = [];
    var sources = buckets[buckets.length - 1];
    var sinks = buckets[0];
    var entry;
    while (g.nodeCount()) {
      while (entry = sinks.dequeue()) {
        removeNode(g, buckets, zeroIdx, entry);
      }
      while (entry = sources.dequeue()) {
        removeNode(g, buckets, zeroIdx, entry);
      }
      if (g.nodeCount()) {
        for (var i = buckets.length - 2; i > 0; --i) {
          entry = buckets[i].dequeue();
          if (entry) {
            results = results.concat(removeNode(g, buckets, zeroIdx, entry, true));
            break;
          }
        }
      }
    }
    return results;
  }
  function removeNode(g, buckets, zeroIdx, entry, collectPredecessors) {
    var results = collectPredecessors ? [] : void 0;
    forEach_default(g.inEdges(entry.v), function(edge) {
      var weight = g.edge(edge);
      var uEntry = g.node(edge.v);
      if (collectPredecessors) {
        results.push({ v: edge.v, w: edge.w });
      }
      uEntry.out -= weight;
      assignBucket(buckets, zeroIdx, uEntry);
    });
    forEach_default(g.outEdges(entry.v), function(edge) {
      var weight = g.edge(edge);
      var w = edge.w;
      var wEntry = g.node(w);
      wEntry["in"] -= weight;
      assignBucket(buckets, zeroIdx, wEntry);
    });
    g.removeNode(entry.v);
    return results;
  }
  function buildState(g, weightFn) {
    var fasGraph = new Graph();
    var maxIn = 0;
    var maxOut = 0;
    forEach_default(g.nodes(), function(v) {
      fasGraph.setNode(v, { v, in: 0, out: 0 });
    });
    forEach_default(g.edges(), function(e) {
      var prevWeight = fasGraph.edge(e.v, e.w) || 0;
      var weight = weightFn(e);
      var edgeWeight = prevWeight + weight;
      fasGraph.setEdge(e.v, e.w, edgeWeight);
      maxOut = Math.max(maxOut, fasGraph.node(e.v).out += weight);
      maxIn = Math.max(maxIn, fasGraph.node(e.w)["in"] += weight);
    });
    var buckets = range_default(maxOut + maxIn + 3).map(function() {
      return new List();
    });
    var zeroIdx = maxIn + 1;
    forEach_default(fasGraph.nodes(), function(v) {
      assignBucket(buckets, zeroIdx, fasGraph.node(v));
    });
    return { graph: fasGraph, buckets, zeroIdx };
  }
  function assignBucket(buckets, zeroIdx, entry) {
    if (!entry.out) {
      buckets[0].enqueue(entry);
    } else if (!entry["in"]) {
      buckets[buckets.length - 1].enqueue(entry);
    } else {
      buckets[entry.out - entry["in"] + zeroIdx].enqueue(entry);
    }
  }

  // node_modules/dagre-d3-es/src/dagre/acyclic.js
  function run(g) {
    var fas = g.graph().acyclicer === "greedy" ? greedyFAS(g, weightFn(g)) : dfsFAS(g);
    forEach_default(fas, function(e) {
      var label = g.edge(e);
      g.removeEdge(e);
      label.forwardName = e.name;
      label.reversed = true;
      g.setEdge(e.w, e.v, label, uniqueId_default("rev"));
    });
    function weightFn(g2) {
      return function(e) {
        return g2.edge(e).weight;
      };
    }
  }
  function dfsFAS(g) {
    var fas = [];
    var stack = {};
    var visited = {};
    function dfs3(v) {
      if (Object.prototype.hasOwnProperty.call(visited, v)) {
        return;
      }
      visited[v] = true;
      stack[v] = true;
      forEach_default(g.outEdges(v), function(e) {
        if (Object.prototype.hasOwnProperty.call(stack, e.w)) {
          fas.push(e);
        } else {
          dfs3(e.w);
        }
      });
      delete stack[v];
    }
    forEach_default(g.nodes(), dfs3);
    return fas;
  }
  function undo(g) {
    forEach_default(g.edges(), function(e) {
      var label = g.edge(e);
      if (label.reversed) {
        g.removeEdge(e);
        var forwardName = label.forwardName;
        delete label.reversed;
        delete label.forwardName;
        g.setEdge(e.w, e.v, label, forwardName);
      }
    });
  }

  // node_modules/dagre-d3-es/src/dagre/util.js
  function addDummyNode(g, type, attrs, name) {
    var v;
    do {
      v = uniqueId_default(name);
    } while (g.hasNode(v));
    attrs.dummy = type;
    g.setNode(v, attrs);
    return v;
  }
  function simplify(g) {
    var simplified = new Graph().setGraph(g.graph());
    forEach_default(g.nodes(), function(v) {
      simplified.setNode(v, g.node(v));
    });
    forEach_default(g.edges(), function(e) {
      var simpleLabel = simplified.edge(e.v, e.w) || { weight: 0, minlen: 1 };
      var label = g.edge(e);
      simplified.setEdge(e.v, e.w, {
        weight: simpleLabel.weight + label.weight,
        minlen: Math.max(simpleLabel.minlen, label.minlen)
      });
    });
    return simplified;
  }
  function asNonCompoundGraph(g) {
    var simplified = new Graph({ multigraph: g.isMultigraph() }).setGraph(g.graph());
    forEach_default(g.nodes(), function(v) {
      if (!g.children(v).length) {
        simplified.setNode(v, g.node(v));
      }
    });
    forEach_default(g.edges(), function(e) {
      simplified.setEdge(e, g.edge(e));
    });
    return simplified;
  }
  function intersectRect(rect2, point) {
    var x = rect2.x;
    var y = rect2.y;
    var dx = point.x - x;
    var dy = point.y - y;
    var w = rect2.width / 2;
    var h = rect2.height / 2;
    if (!dx && !dy) {
      throw new Error("Not possible to find intersection inside of the rectangle");
    }
    var sx, sy;
    if (Math.abs(dy) * w > Math.abs(dx) * h) {
      if (dy < 0) {
        h = -h;
      }
      sx = h * dx / dy;
      sy = h;
    } else {
      if (dx < 0) {
        w = -w;
      }
      sx = w;
      sy = w * dy / dx;
    }
    return { x: x + sx, y: y + sy };
  }
  function buildLayerMatrix(g) {
    var layering = map_default(range_default(maxRank(g) + 1), function() {
      return [];
    });
    forEach_default(g.nodes(), function(v) {
      var node = g.node(v);
      var rank2 = node.rank;
      if (!isUndefined_default(rank2)) {
        layering[rank2][node.order] = v;
      }
    });
    return layering;
  }
  function normalizeRanks(g) {
    var min2 = min_default(
      map_default(g.nodes(), function(v) {
        return g.node(v).rank;
      })
    );
    forEach_default(g.nodes(), function(v) {
      var node = g.node(v);
      if (has_default(node, "rank")) {
        node.rank -= min2;
      }
    });
  }
  function removeEmptyRanks(g) {
    var offset = min_default(
      map_default(g.nodes(), function(v) {
        return g.node(v).rank;
      })
    );
    var layers = [];
    forEach_default(g.nodes(), function(v) {
      var rank2 = g.node(v).rank - offset;
      if (!layers[rank2]) {
        layers[rank2] = [];
      }
      layers[rank2].push(v);
    });
    var delta = 0;
    var nodeRankFactor = g.graph().nodeRankFactor;
    forEach_default(layers, function(vs, i) {
      if (isUndefined_default(vs) && i % nodeRankFactor !== 0) {
        --delta;
      } else if (delta) {
        forEach_default(vs, function(v) {
          g.node(v).rank += delta;
        });
      }
    });
  }
  function addBorderNode(g, prefix, rank2, order2) {
    var node = {
      width: 0,
      height: 0
    };
    if (arguments.length >= 4) {
      node.rank = rank2;
      node.order = order2;
    }
    return addDummyNode(g, "border", node, prefix);
  }
  function maxRank(g) {
    return max_default(
      map_default(g.nodes(), function(v) {
        var rank2 = g.node(v).rank;
        if (!isUndefined_default(rank2)) {
          return rank2;
        }
      })
    );
  }
  function partition(collection, fn) {
    var result = { lhs: [], rhs: [] };
    forEach_default(collection, function(value) {
      if (fn(value)) {
        result.lhs.push(value);
      } else {
        result.rhs.push(value);
      }
    });
    return result;
  }
  function time(name, fn) {
    var start = now_default();
    try {
      return fn();
    } finally {
      console.log(name + " time: " + (now_default() - start) + "ms");
    }
  }
  function notime(name, fn) {
    return fn();
  }

  // node_modules/dagre-d3-es/src/dagre/add-border-segments.js
  function addBorderSegments(g) {
    function dfs3(v) {
      var children = g.children(v);
      var node = g.node(v);
      if (children.length) {
        forEach_default(children, dfs3);
      }
      if (Object.prototype.hasOwnProperty.call(node, "minRank")) {
        node.borderLeft = [];
        node.borderRight = [];
        for (var rank2 = node.minRank, maxRank2 = node.maxRank + 1; rank2 < maxRank2; ++rank2) {
          addBorderNode2(g, "borderLeft", "_bl", v, node, rank2);
          addBorderNode2(g, "borderRight", "_br", v, node, rank2);
        }
      }
    }
    forEach_default(g.children(), dfs3);
  }
  function addBorderNode2(g, prop, prefix, sg, sgNode, rank2) {
    var label = { width: 0, height: 0, rank: rank2, borderType: prop };
    var prev = sgNode[prop][rank2 - 1];
    var curr = addDummyNode(g, "border", label, prefix);
    sgNode[prop][rank2] = curr;
    g.setParent(curr, sg);
    if (prev) {
      g.setEdge(prev, curr, { weight: 1 });
    }
  }

  // node_modules/dagre-d3-es/src/dagre/coordinate-system.js
  function adjust(g) {
    var rankDir = g.graph().rankdir.toLowerCase();
    if (rankDir === "lr" || rankDir === "rl") {
      swapWidthHeight(g);
    }
  }
  function undo2(g) {
    var rankDir = g.graph().rankdir.toLowerCase();
    if (rankDir === "bt" || rankDir === "rl") {
      reverseY(g);
    }
    if (rankDir === "lr" || rankDir === "rl") {
      swapXY(g);
      swapWidthHeight(g);
    }
  }
  function swapWidthHeight(g) {
    forEach_default(g.nodes(), function(v) {
      swapWidthHeightOne(g.node(v));
    });
    forEach_default(g.edges(), function(e) {
      swapWidthHeightOne(g.edge(e));
    });
  }
  function swapWidthHeightOne(attrs) {
    var w = attrs.width;
    attrs.width = attrs.height;
    attrs.height = w;
  }
  function reverseY(g) {
    forEach_default(g.nodes(), function(v) {
      reverseYOne(g.node(v));
    });
    forEach_default(g.edges(), function(e) {
      var edge = g.edge(e);
      forEach_default(edge.points, reverseYOne);
      if (Object.prototype.hasOwnProperty.call(edge, "y")) {
        reverseYOne(edge);
      }
    });
  }
  function reverseYOne(attrs) {
    attrs.y = -attrs.y;
  }
  function swapXY(g) {
    forEach_default(g.nodes(), function(v) {
      swapXYOne(g.node(v));
    });
    forEach_default(g.edges(), function(e) {
      var edge = g.edge(e);
      forEach_default(edge.points, swapXYOne);
      if (Object.prototype.hasOwnProperty.call(edge, "x")) {
        swapXYOne(edge);
      }
    });
  }
  function swapXYOne(attrs) {
    var x = attrs.x;
    attrs.x = attrs.y;
    attrs.y = x;
  }

  // node_modules/dagre-d3-es/src/dagre/normalize.js
  function run2(g) {
    g.graph().dummyChains = [];
    forEach_default(g.edges(), function(edge) {
      normalizeEdge(g, edge);
    });
  }
  function normalizeEdge(g, e) {
    var v = e.v;
    var vRank = g.node(v).rank;
    var w = e.w;
    var wRank = g.node(w).rank;
    var name = e.name;
    var edgeLabel = g.edge(e);
    var labelRank = edgeLabel.labelRank;
    if (wRank === vRank + 1) return;
    g.removeEdge(e);
    var attrs = void 0;
    var dummy, i;
    for (i = 0, ++vRank; vRank < wRank; ++i, ++vRank) {
      edgeLabel.points = [];
      attrs = {
        width: 0,
        height: 0,
        edgeLabel,
        edgeObj: e,
        rank: vRank
      };
      dummy = addDummyNode(g, "edge", attrs, "_d");
      if (vRank === labelRank) {
        attrs.width = edgeLabel.width;
        attrs.height = edgeLabel.height;
        attrs.dummy = "edge-label";
        attrs.labelpos = edgeLabel.labelpos;
      }
      g.setEdge(v, dummy, { weight: edgeLabel.weight }, name);
      if (i === 0) {
        g.graph().dummyChains.push(dummy);
      }
      v = dummy;
    }
    g.setEdge(v, w, { weight: edgeLabel.weight }, name);
  }
  function undo3(g) {
    forEach_default(g.graph().dummyChains, function(v) {
      var node = g.node(v);
      var origLabel = node.edgeLabel;
      var w;
      g.setEdge(node.edgeObj, origLabel);
      while (node.dummy) {
        w = g.successors(v)[0];
        g.removeNode(v);
        origLabel.points.push({ x: node.x, y: node.y });
        if (node.dummy === "edge-label") {
          origLabel.x = node.x;
          origLabel.y = node.y;
          origLabel.width = node.width;
          origLabel.height = node.height;
        }
        v = w;
        node = g.node(v);
      }
    });
  }

  // node_modules/dagre-d3-es/src/dagre/rank/util.js
  function longestPath(g) {
    var visited = {};
    function dfs3(v) {
      var label = g.node(v);
      if (Object.prototype.hasOwnProperty.call(visited, v)) {
        return label.rank;
      }
      visited[v] = true;
      var rank2 = min_default(
        map_default(g.outEdges(v), function(e) {
          return dfs3(e.w) - g.edge(e).minlen;
        })
      );
      if (rank2 === Number.POSITIVE_INFINITY || // return value of _.map([]) for Lodash 3
      rank2 === void 0 || // return value of _.map([]) for Lodash 4
      rank2 === null) {
        rank2 = 0;
      }
      return label.rank = rank2;
    }
    forEach_default(g.sources(), dfs3);
  }
  function slack(g, e) {
    return g.node(e.w).rank - g.node(e.v).rank - g.edge(e).minlen;
  }

  // node_modules/dagre-d3-es/src/dagre/rank/feasible-tree.js
  function feasibleTree(g) {
    var t = new Graph({ directed: false });
    var start = g.nodes()[0];
    var size2 = g.nodeCount();
    t.setNode(start, {});
    var edge, delta;
    while (tightTree(t, g) < size2) {
      edge = findMinSlackEdge(t, g);
      delta = t.hasNode(edge.v) ? slack(g, edge) : -slack(g, edge);
      shiftRanks(t, g, delta);
    }
    return t;
  }
  function tightTree(t, g) {
    function dfs3(v) {
      forEach_default(g.nodeEdges(v), function(e) {
        var edgeV = e.v, w = v === edgeV ? e.w : edgeV;
        if (!t.hasNode(w) && !slack(g, e)) {
          t.setNode(w, {});
          t.setEdge(v, w, {});
          dfs3(w);
        }
      });
    }
    forEach_default(t.nodes(), dfs3);
    return t.nodeCount();
  }
  function findMinSlackEdge(t, g) {
    return minBy_default(g.edges(), function(e) {
      if (t.hasNode(e.v) !== t.hasNode(e.w)) {
        return slack(g, e);
      }
    });
  }
  function shiftRanks(t, g, delta) {
    forEach_default(t.nodes(), function(v) {
      g.node(v).rank += delta;
    });
  }

  // node_modules/dagre-d3-es/src/graphlib/alg/dijkstra.js
  var DEFAULT_WEIGHT_FUNC = constant_default(1);

  // node_modules/dagre-d3-es/src/graphlib/alg/floyd-warshall.js
  var DEFAULT_WEIGHT_FUNC2 = constant_default(1);

  // node_modules/dagre-d3-es/src/graphlib/alg/topsort.js
  topsort.CycleException = CycleException;
  function topsort(g) {
    var visited = {};
    var stack = {};
    var results = [];
    function visit(node) {
      if (Object.prototype.hasOwnProperty.call(stack, node)) {
        throw new CycleException();
      }
      if (!Object.prototype.hasOwnProperty.call(visited, node)) {
        stack[node] = true;
        visited[node] = true;
        forEach_default(g.predecessors(node), visit);
        delete stack[node];
        results.push(node);
      }
    }
    forEach_default(g.sinks(), visit);
    if (size_default(visited) !== g.nodeCount()) {
      throw new CycleException();
    }
    return results;
  }
  function CycleException() {
  }
  CycleException.prototype = new Error();

  // node_modules/dagre-d3-es/src/graphlib/alg/dfs.js
  function dfs(g, vs, order2) {
    if (!isArray_default(vs)) {
      vs = [vs];
    }
    var navigation = (g.isDirected() ? g.successors : g.neighbors).bind(g);
    var acc = [];
    var visited = {};
    forEach_default(vs, function(v) {
      if (!g.hasNode(v)) {
        throw new Error("Graph does not have node: " + v);
      }
      doDfs(g, v, order2 === "post", visited, navigation, acc);
    });
    return acc;
  }
  function doDfs(g, v, postorder3, visited, navigation, acc) {
    if (!Object.prototype.hasOwnProperty.call(visited, v)) {
      visited[v] = true;
      if (!postorder3) {
        acc.push(v);
      }
      forEach_default(navigation(v), function(w) {
        doDfs(g, w, postorder3, visited, navigation, acc);
      });
      if (postorder3) {
        acc.push(v);
      }
    }
  }

  // node_modules/dagre-d3-es/src/graphlib/alg/postorder.js
  function postorder(g, vs) {
    return dfs(g, vs, "post");
  }

  // node_modules/dagre-d3-es/src/graphlib/alg/preorder.js
  function preorder(g, vs) {
    return dfs(g, vs, "pre");
  }

  // node_modules/dagre-d3-es/src/dagre/rank/network-simplex.js
  networkSimplex.initLowLimValues = initLowLimValues;
  networkSimplex.initCutValues = initCutValues;
  networkSimplex.calcCutValue = calcCutValue;
  networkSimplex.leaveEdge = leaveEdge;
  networkSimplex.enterEdge = enterEdge;
  networkSimplex.exchangeEdges = exchangeEdges;
  function networkSimplex(g) {
    g = simplify(g);
    longestPath(g);
    var t = feasibleTree(g);
    initLowLimValues(t);
    initCutValues(t, g);
    var e, f;
    while (e = leaveEdge(t)) {
      f = enterEdge(t, g, e);
      exchangeEdges(t, g, e, f);
    }
  }
  function initCutValues(t, g) {
    var vs = postorder(t, t.nodes());
    vs = vs.slice(0, vs.length - 1);
    forEach_default(vs, function(v) {
      assignCutValue(t, g, v);
    });
  }
  function assignCutValue(t, g, child) {
    var childLab = t.node(child);
    var parent = childLab.parent;
    t.edge(child, parent).cutvalue = calcCutValue(t, g, child);
  }
  function calcCutValue(t, g, child) {
    var childLab = t.node(child);
    var parent = childLab.parent;
    var childIsTail = true;
    var graphEdge = g.edge(child, parent);
    var cutValue = 0;
    if (!graphEdge) {
      childIsTail = false;
      graphEdge = g.edge(parent, child);
    }
    cutValue = graphEdge.weight;
    forEach_default(g.nodeEdges(child), function(e) {
      var isOutEdge = e.v === child, other = isOutEdge ? e.w : e.v;
      if (other !== parent) {
        var pointsToHead = isOutEdge === childIsTail, otherWeight = g.edge(e).weight;
        cutValue += pointsToHead ? otherWeight : -otherWeight;
        if (isTreeEdge(t, child, other)) {
          var otherCutValue = t.edge(child, other).cutvalue;
          cutValue += pointsToHead ? -otherCutValue : otherCutValue;
        }
      }
    });
    return cutValue;
  }
  function initLowLimValues(tree, root2) {
    if (arguments.length < 2) {
      root2 = tree.nodes()[0];
    }
    dfsAssignLowLim(tree, {}, 1, root2);
  }
  function dfsAssignLowLim(tree, visited, nextLim, v, parent) {
    var low = nextLim;
    var label = tree.node(v);
    visited[v] = true;
    forEach_default(tree.neighbors(v), function(w) {
      if (!Object.prototype.hasOwnProperty.call(visited, w)) {
        nextLim = dfsAssignLowLim(tree, visited, nextLim, w, v);
      }
    });
    label.low = low;
    label.lim = nextLim++;
    if (parent) {
      label.parent = parent;
    } else {
      delete label.parent;
    }
    return nextLim;
  }
  function leaveEdge(tree) {
    return find_default(tree.edges(), function(e) {
      return tree.edge(e).cutvalue < 0;
    });
  }
  function enterEdge(t, g, edge) {
    var v = edge.v;
    var w = edge.w;
    if (!g.hasEdge(v, w)) {
      v = edge.w;
      w = edge.v;
    }
    var vLabel = t.node(v);
    var wLabel = t.node(w);
    var tailLabel = vLabel;
    var flip = false;
    if (vLabel.lim > wLabel.lim) {
      tailLabel = wLabel;
      flip = true;
    }
    var candidates = filter_default(g.edges(), function(edge2) {
      return flip === isDescendant(t, t.node(edge2.v), tailLabel) && flip !== isDescendant(t, t.node(edge2.w), tailLabel);
    });
    return minBy_default(candidates, function(edge2) {
      return slack(g, edge2);
    });
  }
  function exchangeEdges(t, g, e, f) {
    var v = e.v;
    var w = e.w;
    t.removeEdge(v, w);
    t.setEdge(f.v, f.w, {});
    initLowLimValues(t);
    initCutValues(t, g);
    updateRanks(t, g);
  }
  function updateRanks(t, g) {
    var root2 = find_default(t.nodes(), function(v) {
      return !g.node(v).parent;
    });
    var vs = preorder(t, root2);
    vs = vs.slice(1);
    forEach_default(vs, function(v) {
      var parent = t.node(v).parent, edge = g.edge(v, parent), flipped = false;
      if (!edge) {
        edge = g.edge(parent, v);
        flipped = true;
      }
      g.node(v).rank = g.node(parent).rank + (flipped ? edge.minlen : -edge.minlen);
    });
  }
  function isTreeEdge(tree, u, v) {
    return tree.hasEdge(u, v);
  }
  function isDescendant(tree, vLabel, rootLabel) {
    return rootLabel.low <= vLabel.lim && vLabel.lim <= rootLabel.lim;
  }

  // node_modules/dagre-d3-es/src/dagre/rank/index.js
  function rank(g) {
    switch (g.graph().ranker) {
      case "network-simplex":
        networkSimplexRanker(g);
        break;
      case "tight-tree":
        tightTreeRanker(g);
        break;
      case "longest-path":
        longestPathRanker(g);
        break;
      default:
        networkSimplexRanker(g);
    }
  }
  var longestPathRanker = longestPath;
  function tightTreeRanker(g) {
    longestPath(g);
    feasibleTree(g);
  }
  function networkSimplexRanker(g) {
    networkSimplex(g);
  }

  // node_modules/dagre-d3-es/src/dagre/nesting-graph.js
  function run3(g) {
    var root2 = addDummyNode(g, "root", {}, "_root");
    var depths = treeDepths(g);
    var height = max_default(values_default(depths)) - 1;
    var nodeSep = 2 * height + 1;
    g.graph().nestingRoot = root2;
    forEach_default(g.edges(), function(e) {
      g.edge(e).minlen *= nodeSep;
    });
    var weight = sumWeights(g) + 1;
    forEach_default(g.children(), function(child) {
      dfs2(g, root2, nodeSep, weight, height, depths, child);
    });
    g.graph().nodeRankFactor = nodeSep;
  }
  function dfs2(g, root2, nodeSep, weight, height, depths, v) {
    var children = g.children(v);
    if (!children.length) {
      if (v !== root2) {
        g.setEdge(root2, v, { weight: 0, minlen: nodeSep });
      }
      return;
    }
    var top = addBorderNode(g, "_bt");
    var bottom = addBorderNode(g, "_bb");
    var label = g.node(v);
    g.setParent(top, v);
    label.borderTop = top;
    g.setParent(bottom, v);
    label.borderBottom = bottom;
    forEach_default(children, function(child) {
      dfs2(g, root2, nodeSep, weight, height, depths, child);
      var childNode = g.node(child);
      var childTop = childNode.borderTop ? childNode.borderTop : child;
      var childBottom = childNode.borderBottom ? childNode.borderBottom : child;
      var thisWeight = childNode.borderTop ? weight : 2 * weight;
      var minlen = childTop !== childBottom ? 1 : height - depths[v] + 1;
      g.setEdge(top, childTop, {
        weight: thisWeight,
        minlen,
        nestingEdge: true
      });
      g.setEdge(childBottom, bottom, {
        weight: thisWeight,
        minlen,
        nestingEdge: true
      });
    });
    if (!g.parent(v)) {
      g.setEdge(root2, top, { weight: 0, minlen: height + depths[v] });
    }
  }
  function treeDepths(g) {
    var depths = {};
    function dfs3(v, depth) {
      var children = g.children(v);
      if (children && children.length) {
        forEach_default(children, function(child) {
          dfs3(child, depth + 1);
        });
      }
      depths[v] = depth;
    }
    forEach_default(g.children(), function(v) {
      dfs3(v, 1);
    });
    return depths;
  }
  function sumWeights(g) {
    return reduce_default(
      g.edges(),
      function(acc, e) {
        return acc + g.edge(e).weight;
      },
      0
    );
  }
  function cleanup(g) {
    var graphLabel = g.graph();
    g.removeNode(graphLabel.nestingRoot);
    delete graphLabel.nestingRoot;
    forEach_default(g.edges(), function(e) {
      var edge = g.edge(e);
      if (edge.nestingEdge) {
        g.removeEdge(e);
      }
    });
  }

  // node_modules/dagre-d3-es/src/dagre/order/add-subgraph-constraints.js
  function addSubgraphConstraints(g, cg, vs) {
    var prev = {}, rootPrev;
    forEach_default(vs, function(v) {
      var child = g.parent(v), parent, prevChild;
      while (child) {
        parent = g.parent(child);
        if (parent) {
          prevChild = prev[parent];
          prev[parent] = child;
        } else {
          prevChild = rootPrev;
          rootPrev = child;
        }
        if (prevChild && prevChild !== child) {
          cg.setEdge(prevChild, child);
          return;
        }
        child = parent;
      }
    });
  }

  // node_modules/dagre-d3-es/src/dagre/order/build-layer-graph.js
  function buildLayerGraph(g, rank2, relationship) {
    var root2 = createRootNode(g), result = new Graph({ compound: true }).setGraph({ root: root2 }).setDefaultNodeLabel(function(v) {
      return g.node(v);
    });
    forEach_default(g.nodes(), function(v) {
      var node = g.node(v), parent = g.parent(v);
      if (node.rank === rank2 || node.minRank <= rank2 && rank2 <= node.maxRank) {
        result.setNode(v);
        result.setParent(v, parent || root2);
        forEach_default(g[relationship](v), function(e) {
          var u = e.v === v ? e.w : e.v, edge = result.edge(u, v), weight = !isUndefined_default(edge) ? edge.weight : 0;
          result.setEdge(u, v, { weight: g.edge(e).weight + weight });
        });
        if (Object.prototype.hasOwnProperty.call(node, "minRank")) {
          result.setNode(v, {
            borderLeft: node.borderLeft[rank2],
            borderRight: node.borderRight[rank2]
          });
        }
      }
    });
    return result;
  }
  function createRootNode(g) {
    var v;
    while (g.hasNode(v = uniqueId_default("_root"))) ;
    return v;
  }

  // node_modules/dagre-d3-es/src/dagre/order/cross-count.js
  function crossCount(g, layering) {
    var cc = 0;
    for (var i = 1; i < layering.length; ++i) {
      cc += twoLayerCrossCount(g, layering[i - 1], layering[i]);
    }
    return cc;
  }
  function twoLayerCrossCount(g, northLayer, southLayer) {
    var southPos = zipObject_default(
      southLayer,
      map_default(southLayer, function(v, i) {
        return i;
      })
    );
    var southEntries = flatten_default(
      map_default(northLayer, function(v) {
        return sortBy_default(
          map_default(g.outEdges(v), function(e) {
            return { pos: southPos[e.w], weight: g.edge(e).weight };
          }),
          "pos"
        );
      })
    );
    var firstIndex = 1;
    while (firstIndex < southLayer.length) firstIndex <<= 1;
    var treeSize = 2 * firstIndex - 1;
    firstIndex -= 1;
    var tree = map_default(new Array(treeSize), function() {
      return 0;
    });
    var cc = 0;
    forEach_default(
      // @ts-expect-error
      southEntries.forEach(function(entry) {
        var index = entry.pos + firstIndex;
        tree[index] += entry.weight;
        var weightSum = 0;
        while (index > 0) {
          if (index % 2) {
            weightSum += tree[index + 1];
          }
          index = index - 1 >> 1;
          tree[index] += entry.weight;
        }
        cc += entry.weight * weightSum;
      })
    );
    return cc;
  }

  // node_modules/dagre-d3-es/src/dagre/order/init-order.js
  function initOrder(g) {
    var visited = {};
    var simpleNodes = filter_default(g.nodes(), function(v) {
      return !g.children(v).length;
    });
    var maxRank2 = max_default(
      map_default(simpleNodes, function(v) {
        return g.node(v).rank;
      })
    );
    var layers = map_default(range_default(maxRank2 + 1), function() {
      return [];
    });
    function dfs3(v) {
      if (has_default(visited, v)) return;
      visited[v] = true;
      var node = g.node(v);
      layers[node.rank].push(v);
      forEach_default(g.successors(v), dfs3);
    }
    var orderedVs = sortBy_default(simpleNodes, function(v) {
      return g.node(v).rank;
    });
    forEach_default(orderedVs, dfs3);
    return layers;
  }

  // node_modules/dagre-d3-es/src/dagre/order/barycenter.js
  function barycenter(g, movable) {
    return map_default(movable, function(v) {
      var inV = g.inEdges(v);
      if (!inV.length) {
        return { v };
      } else {
        var result = reduce_default(
          inV,
          function(acc, e) {
            var edge = g.edge(e), nodeU = g.node(e.v);
            return {
              sum: acc.sum + edge.weight * nodeU.order,
              weight: acc.weight + edge.weight
            };
          },
          { sum: 0, weight: 0 }
        );
        return {
          v,
          barycenter: result.sum / result.weight,
          weight: result.weight
        };
      }
    });
  }

  // node_modules/dagre-d3-es/src/dagre/order/resolve-conflicts.js
  function resolveConflicts(entries, cg) {
    var mappedEntries = {};
    forEach_default(entries, function(entry, i) {
      var tmp = mappedEntries[entry.v] = {
        indegree: 0,
        in: [],
        out: [],
        vs: [entry.v],
        i
      };
      if (!isUndefined_default(entry.barycenter)) {
        tmp.barycenter = entry.barycenter;
        tmp.weight = entry.weight;
      }
    });
    forEach_default(cg.edges(), function(e) {
      var entryV = mappedEntries[e.v];
      var entryW = mappedEntries[e.w];
      if (!isUndefined_default(entryV) && !isUndefined_default(entryW)) {
        entryW.indegree++;
        entryV.out.push(mappedEntries[e.w]);
      }
    });
    var sourceSet = filter_default(mappedEntries, function(entry) {
      return !entry.indegree;
    });
    return doResolveConflicts(sourceSet);
  }
  function doResolveConflicts(sourceSet) {
    var entries = [];
    function handleIn(vEntry) {
      return function(uEntry) {
        if (uEntry.merged) {
          return;
        }
        if (isUndefined_default(uEntry.barycenter) || isUndefined_default(vEntry.barycenter) || uEntry.barycenter >= vEntry.barycenter) {
          mergeEntries(vEntry, uEntry);
        }
      };
    }
    function handleOut(vEntry) {
      return function(wEntry) {
        wEntry["in"].push(vEntry);
        if (--wEntry.indegree === 0) {
          sourceSet.push(wEntry);
        }
      };
    }
    while (sourceSet.length) {
      var entry = sourceSet.pop();
      entries.push(entry);
      forEach_default(entry["in"].reverse(), handleIn(entry));
      forEach_default(entry.out, handleOut(entry));
    }
    return map_default(
      filter_default(entries, function(entry2) {
        return !entry2.merged;
      }),
      function(entry2) {
        return pick_default(entry2, ["vs", "i", "barycenter", "weight"]);
      }
    );
  }
  function mergeEntries(target, source) {
    var sum = 0;
    var weight = 0;
    if (target.weight) {
      sum += target.barycenter * target.weight;
      weight += target.weight;
    }
    if (source.weight) {
      sum += source.barycenter * source.weight;
      weight += source.weight;
    }
    target.vs = source.vs.concat(target.vs);
    target.barycenter = sum / weight;
    target.weight = weight;
    target.i = Math.min(source.i, target.i);
    source.merged = true;
  }

  // node_modules/dagre-d3-es/src/dagre/order/sort.js
  function sort(entries, biasRight) {
    var parts = partition(entries, function(entry) {
      return Object.prototype.hasOwnProperty.call(entry, "barycenter");
    });
    var sortable = parts.lhs, unsortable = sortBy_default(parts.rhs, function(entry) {
      return -entry.i;
    }), vs = [], sum = 0, weight = 0, vsIndex = 0;
    sortable.sort(compareWithBias(!!biasRight));
    vsIndex = consumeUnsortable(vs, unsortable, vsIndex);
    forEach_default(sortable, function(entry) {
      vsIndex += entry.vs.length;
      vs.push(entry.vs);
      sum += entry.barycenter * entry.weight;
      weight += entry.weight;
      vsIndex = consumeUnsortable(vs, unsortable, vsIndex);
    });
    var result = { vs: flatten_default(vs) };
    if (weight) {
      result.barycenter = sum / weight;
      result.weight = weight;
    }
    return result;
  }
  function consumeUnsortable(vs, unsortable, index) {
    var last2;
    while (unsortable.length && (last2 = last_default(unsortable)).i <= index) {
      unsortable.pop();
      vs.push(last2.vs);
      index++;
    }
    return index;
  }
  function compareWithBias(bias) {
    return function(entryV, entryW) {
      if (entryV.barycenter < entryW.barycenter) {
        return -1;
      } else if (entryV.barycenter > entryW.barycenter) {
        return 1;
      }
      return !bias ? entryV.i - entryW.i : entryW.i - entryV.i;
    };
  }

  // node_modules/dagre-d3-es/src/dagre/order/sort-subgraph.js
  function sortSubgraph(g, v, cg, biasRight) {
    var movable = g.children(v);
    var node = g.node(v);
    var bl = node ? node.borderLeft : void 0;
    var br = node ? node.borderRight : void 0;
    var subgraphs = {};
    if (bl) {
      movable = filter_default(movable, function(w) {
        return w !== bl && w !== br;
      });
    }
    var barycenters = barycenter(g, movable);
    forEach_default(barycenters, function(entry) {
      if (g.children(entry.v).length) {
        var subgraphResult = sortSubgraph(g, entry.v, cg, biasRight);
        subgraphs[entry.v] = subgraphResult;
        if (Object.prototype.hasOwnProperty.call(subgraphResult, "barycenter")) {
          mergeBarycenters(entry, subgraphResult);
        }
      }
    });
    var entries = resolveConflicts(barycenters, cg);
    expandSubgraphs(entries, subgraphs);
    var result = sort(entries, biasRight);
    if (bl) {
      result.vs = flatten_default([bl, result.vs, br]);
      if (g.predecessors(bl).length) {
        var blPred = g.node(g.predecessors(bl)[0]), brPred = g.node(g.predecessors(br)[0]);
        if (!Object.prototype.hasOwnProperty.call(result, "barycenter")) {
          result.barycenter = 0;
          result.weight = 0;
        }
        result.barycenter = (result.barycenter * result.weight + blPred.order + brPred.order) / (result.weight + 2);
        result.weight += 2;
      }
    }
    return result;
  }
  function expandSubgraphs(entries, subgraphs) {
    forEach_default(entries, function(entry) {
      entry.vs = flatten_default(
        entry.vs.map(function(v) {
          if (subgraphs[v]) {
            return subgraphs[v].vs;
          }
          return v;
        })
      );
    });
  }
  function mergeBarycenters(target, other) {
    if (!isUndefined_default(target.barycenter)) {
      target.barycenter = (target.barycenter * target.weight + other.barycenter * other.weight) / (target.weight + other.weight);
      target.weight += other.weight;
    } else {
      target.barycenter = other.barycenter;
      target.weight = other.weight;
    }
  }

  // node_modules/dagre-d3-es/src/dagre/order/index.js
  function order(g) {
    var maxRank2 = maxRank(g), downLayerGraphs = buildLayerGraphs(g, range_default(1, maxRank2 + 1), "inEdges"), upLayerGraphs = buildLayerGraphs(g, range_default(maxRank2 - 1, -1, -1), "outEdges");
    var layering = initOrder(g);
    assignOrder(g, layering);
    var bestCC = Number.POSITIVE_INFINITY, best;
    for (var i = 0, lastBest = 0; lastBest < 4; ++i, ++lastBest) {
      sweepLayerGraphs(i % 2 ? downLayerGraphs : upLayerGraphs, i % 4 >= 2);
      layering = buildLayerMatrix(g);
      var cc = crossCount(g, layering);
      if (cc < bestCC) {
        lastBest = 0;
        best = cloneDeep_default(layering);
        bestCC = cc;
      }
    }
    assignOrder(g, best);
  }
  function buildLayerGraphs(g, ranks, relationship) {
    return map_default(ranks, function(rank2) {
      return buildLayerGraph(g, rank2, relationship);
    });
  }
  function sweepLayerGraphs(layerGraphs, biasRight) {
    var cg = new Graph();
    forEach_default(layerGraphs, function(lg) {
      var root2 = lg.graph().root;
      var sorted = sortSubgraph(lg, root2, cg, biasRight);
      forEach_default(sorted.vs, function(v, i) {
        lg.node(v).order = i;
      });
      addSubgraphConstraints(lg, cg, sorted.vs);
    });
  }
  function assignOrder(g, layering) {
    forEach_default(layering, function(layer) {
      forEach_default(layer, function(v, i) {
        g.node(v).order = i;
      });
    });
  }

  // node_modules/dagre-d3-es/src/dagre/parent-dummy-chains.js
  function parentDummyChains(g) {
    var postorderNums = postorder2(g);
    forEach_default(g.graph().dummyChains, function(v) {
      var node = g.node(v);
      var edgeObj = node.edgeObj;
      var pathData = findPath(g, postorderNums, edgeObj.v, edgeObj.w);
      var path = pathData.path;
      var lca = pathData.lca;
      var pathIdx = 0;
      var pathV = path[pathIdx];
      var ascending = true;
      while (v !== edgeObj.w) {
        node = g.node(v);
        if (ascending) {
          while ((pathV = path[pathIdx]) !== lca && g.node(pathV).maxRank < node.rank) {
            pathIdx++;
          }
          if (pathV === lca) {
            ascending = false;
          }
        }
        if (!ascending) {
          while (pathIdx < path.length - 1 && g.node(pathV = path[pathIdx + 1]).minRank <= node.rank) {
            pathIdx++;
          }
          pathV = path[pathIdx];
        }
        g.setParent(v, pathV);
        v = g.successors(v)[0];
      }
    });
  }
  function findPath(g, postorderNums, v, w) {
    var vPath = [];
    var wPath = [];
    var low = Math.min(postorderNums[v].low, postorderNums[w].low);
    var lim = Math.max(postorderNums[v].lim, postorderNums[w].lim);
    var parent;
    var lca;
    parent = v;
    do {
      parent = g.parent(parent);
      vPath.push(parent);
    } while (parent && (postorderNums[parent].low > low || lim > postorderNums[parent].lim));
    lca = parent;
    parent = w;
    while ((parent = g.parent(parent)) !== lca) {
      wPath.push(parent);
    }
    return { path: vPath.concat(wPath.reverse()), lca };
  }
  function postorder2(g) {
    var result = {};
    var lim = 0;
    function dfs3(v) {
      var low = lim;
      forEach_default(g.children(v), dfs3);
      result[v] = { low, lim: lim++ };
    }
    forEach_default(g.children(), dfs3);
    return result;
  }

  // node_modules/dagre-d3-es/src/dagre/position/bk.js
  function findType1Conflicts(g, layering) {
    var conflicts = {};
    function visitLayer(prevLayer, layer) {
      var k0 = 0, scanPos = 0, prevLayerLength = prevLayer.length, lastNode = last_default(layer);
      forEach_default(layer, function(v, i) {
        var w = findOtherInnerSegmentNode(g, v), k1 = w ? g.node(w).order : prevLayerLength;
        if (w || v === lastNode) {
          forEach_default(layer.slice(scanPos, i + 1), function(scanNode) {
            forEach_default(g.predecessors(scanNode), function(u) {
              var uLabel = g.node(u), uPos = uLabel.order;
              if ((uPos < k0 || k1 < uPos) && !(uLabel.dummy && g.node(scanNode).dummy)) {
                addConflict(conflicts, u, scanNode);
              }
            });
          });
          scanPos = i + 1;
          k0 = k1;
        }
      });
      return layer;
    }
    reduce_default(layering, visitLayer);
    return conflicts;
  }
  function findType2Conflicts(g, layering) {
    var conflicts = {};
    function scan(south, southPos, southEnd, prevNorthBorder, nextNorthBorder) {
      var v;
      forEach_default(range_default(southPos, southEnd), function(i) {
        v = south[i];
        if (g.node(v).dummy) {
          forEach_default(g.predecessors(v), function(u) {
            var uNode = g.node(u);
            if (uNode.dummy && (uNode.order < prevNorthBorder || uNode.order > nextNorthBorder)) {
              addConflict(conflicts, u, v);
            }
          });
        }
      });
    }
    function visitLayer(north, south) {
      var prevNorthPos = -1, nextNorthPos, southPos = 0;
      forEach_default(south, function(v, southLookahead) {
        if (g.node(v).dummy === "border") {
          var predecessors = g.predecessors(v);
          if (predecessors.length) {
            nextNorthPos = g.node(predecessors[0]).order;
            scan(south, southPos, southLookahead, prevNorthPos, nextNorthPos);
            southPos = southLookahead;
            prevNorthPos = nextNorthPos;
          }
        }
        scan(south, southPos, south.length, nextNorthPos, north.length);
      });
      return south;
    }
    reduce_default(layering, visitLayer);
    return conflicts;
  }
  function findOtherInnerSegmentNode(g, v) {
    if (g.node(v).dummy) {
      return find_default(g.predecessors(v), function(u) {
        return g.node(u).dummy;
      });
    }
  }
  function addConflict(conflicts, v, w) {
    if (v > w) {
      var tmp = v;
      v = w;
      w = tmp;
    }
    if (!Object.prototype.hasOwnProperty.call(conflicts, v)) {
      Object.defineProperty(conflicts, v, {
        enumerable: true,
        configurable: true,
        value: {},
        writable: true
      });
    }
    var conflictsV = conflicts[v];
    Object.defineProperty(conflictsV, w, {
      enumerable: true,
      configurable: true,
      value: true,
      writable: true
    });
  }
  function hasConflict(conflicts, v, w) {
    if (v > w) {
      var tmp = v;
      v = w;
      w = tmp;
    }
    return !!conflicts[v] && Object.prototype.hasOwnProperty.call(conflicts[v], w);
  }
  function verticalAlignment(g, layering, conflicts, neighborFn) {
    var root2 = {}, align = {}, pos = {};
    forEach_default(layering, function(layer) {
      forEach_default(layer, function(v, order2) {
        root2[v] = v;
        align[v] = v;
        pos[v] = order2;
      });
    });
    forEach_default(layering, function(layer) {
      var prevIdx = -1;
      forEach_default(layer, function(v) {
        var ws = neighborFn(v);
        if (ws.length) {
          ws = sortBy_default(ws, function(w2) {
            return pos[w2];
          });
          var mp = (ws.length - 1) / 2;
          for (var i = Math.floor(mp), il = Math.ceil(mp); i <= il; ++i) {
            var w = ws[i];
            if (align[v] === v && prevIdx < pos[w] && !hasConflict(conflicts, v, w)) {
              align[w] = v;
              align[v] = root2[v] = root2[w];
              prevIdx = pos[w];
            }
          }
        }
      });
    });
    return { root: root2, align };
  }
  function horizontalCompaction(g, layering, root2, align, reverseSep) {
    var xs = {}, blockG = buildBlockGraph(g, layering, root2, reverseSep), borderType = reverseSep ? "borderLeft" : "borderRight";
    function iterate(setXsFunc, nextNodesFunc) {
      var stack = blockG.nodes();
      var elem = stack.pop();
      var visited = {};
      while (elem) {
        if (visited[elem]) {
          setXsFunc(elem);
        } else {
          visited[elem] = true;
          stack.push(elem);
          stack = stack.concat(nextNodesFunc(elem));
        }
        elem = stack.pop();
      }
    }
    function pass1(elem) {
      xs[elem] = blockG.inEdges(elem).reduce(function(acc, e) {
        return Math.max(acc, xs[e.v] + blockG.edge(e));
      }, 0);
    }
    function pass2(elem) {
      var min2 = blockG.outEdges(elem).reduce(function(acc, e) {
        return Math.min(acc, xs[e.w] - blockG.edge(e));
      }, Number.POSITIVE_INFINITY);
      var node = g.node(elem);
      if (min2 !== Number.POSITIVE_INFINITY && node.borderType !== borderType) {
        xs[elem] = Math.max(xs[elem], min2);
      }
    }
    iterate(pass1, blockG.predecessors.bind(blockG));
    iterate(pass2, blockG.successors.bind(blockG));
    forEach_default(align, function(v) {
      xs[v] = xs[root2[v]];
    });
    return xs;
  }
  function buildBlockGraph(g, layering, root2, reverseSep) {
    var blockGraph = new Graph(), graphLabel = g.graph(), sepFn = sep(graphLabel.nodesep, graphLabel.edgesep, reverseSep);
    forEach_default(layering, function(layer) {
      var u;
      forEach_default(layer, function(v) {
        var vRoot = root2[v];
        blockGraph.setNode(vRoot);
        if (u) {
          var uRoot = root2[u], prevMax = blockGraph.edge(uRoot, vRoot);
          blockGraph.setEdge(uRoot, vRoot, Math.max(sepFn(g, v, u), prevMax || 0));
        }
        u = v;
      });
    });
    return blockGraph;
  }
  function findSmallestWidthAlignment(g, xss) {
    return minBy_default(values_default(xss), function(xs) {
      var max2 = Number.NEGATIVE_INFINITY;
      var min2 = Number.POSITIVE_INFINITY;
      forIn_default(xs, function(x, v) {
        var halfWidth = width(g, v) / 2;
        max2 = Math.max(x + halfWidth, max2);
        min2 = Math.min(x - halfWidth, min2);
      });
      return max2 - min2;
    });
  }
  function alignCoordinates(xss, alignTo) {
    var alignToVals = values_default(alignTo), alignToMin = min_default(alignToVals), alignToMax = max_default(alignToVals);
    forEach_default(["u", "d"], function(vert) {
      forEach_default(["l", "r"], function(horiz) {
        var alignment = vert + horiz, xs = xss[alignment], delta;
        if (xs === alignTo) return;
        var xsVals = values_default(xs);
        delta = horiz === "l" ? alignToMin - min_default(xsVals) : alignToMax - max_default(xsVals);
        if (delta) {
          xss[alignment] = mapValues_default(xs, function(x) {
            return x + delta;
          });
        }
      });
    });
  }
  function balance(xss, align) {
    return mapValues_default(xss.ul, function(ignore, v) {
      if (align) {
        return xss[align.toLowerCase()][v];
      } else {
        var xs = sortBy_default(map_default(xss, v));
        return (xs[1] + xs[2]) / 2;
      }
    });
  }
  function positionX(g) {
    var layering = buildLayerMatrix(g);
    var conflicts = merge_default(findType1Conflicts(g, layering), findType2Conflicts(g, layering));
    var xss = {};
    var adjustedLayering;
    forEach_default(["u", "d"], function(vert) {
      adjustedLayering = vert === "u" ? layering : values_default(layering).reverse();
      forEach_default(["l", "r"], function(horiz) {
        if (horiz === "r") {
          adjustedLayering = map_default(adjustedLayering, function(inner) {
            return values_default(inner).reverse();
          });
        }
        var neighborFn = (vert === "u" ? g.predecessors : g.successors).bind(g);
        var align = verticalAlignment(g, adjustedLayering, conflicts, neighborFn);
        var xs = horizontalCompaction(g, adjustedLayering, align.root, align.align, horiz === "r");
        if (horiz === "r") {
          xs = mapValues_default(xs, function(x) {
            return -x;
          });
        }
        xss[vert + horiz] = xs;
      });
    });
    var smallestWidth = findSmallestWidthAlignment(g, xss);
    alignCoordinates(xss, smallestWidth);
    return balance(xss, g.graph().align);
  }
  function sep(nodeSep, edgeSep, reverseSep) {
    return function(g, v, w) {
      var vLabel = g.node(v);
      var wLabel = g.node(w);
      var sum = 0;
      var delta;
      sum += vLabel.width / 2;
      if (Object.prototype.hasOwnProperty.call(vLabel, "labelpos")) {
        switch (vLabel.labelpos.toLowerCase()) {
          case "l":
            delta = -vLabel.width / 2;
            break;
          case "r":
            delta = vLabel.width / 2;
            break;
        }
      }
      if (delta) {
        sum += reverseSep ? delta : -delta;
      }
      delta = 0;
      sum += (vLabel.dummy ? edgeSep : nodeSep) / 2;
      sum += (wLabel.dummy ? edgeSep : nodeSep) / 2;
      sum += wLabel.width / 2;
      if (Object.prototype.hasOwnProperty.call(wLabel, "labelpos")) {
        switch (wLabel.labelpos.toLowerCase()) {
          case "l":
            delta = wLabel.width / 2;
            break;
          case "r":
            delta = -wLabel.width / 2;
            break;
        }
      }
      if (delta) {
        sum += reverseSep ? delta : -delta;
      }
      delta = 0;
      return sum;
    };
  }
  function width(g, v) {
    return g.node(v).width;
  }

  // node_modules/dagre-d3-es/src/dagre/position/index.js
  function position(g) {
    g = asNonCompoundGraph(g);
    positionY(g);
    forOwn_default(positionX(g), function(x, v) {
      g.node(v).x = x;
    });
  }
  function positionY(g) {
    var layering = buildLayerMatrix(g);
    var rankSep = g.graph().ranksep;
    var prevY = 0;
    forEach_default(layering, function(layer) {
      var maxHeight = max_default(
        map_default(layer, function(v) {
          return g.node(v).height;
        })
      );
      forEach_default(layer, function(v) {
        g.node(v).y = prevY + maxHeight / 2;
      });
      prevY += maxHeight + rankSep;
    });
  }

  // node_modules/dagre-d3-es/src/dagre/layout.js
  function layout(g, opts) {
    var time2 = opts && opts.debugTiming ? time : notime;
    time2("layout", () => {
      var layoutGraph = time2("  buildLayoutGraph", () => buildLayoutGraph(g));
      time2("  runLayout", () => runLayout(layoutGraph, time2));
      time2("  updateInputGraph", () => updateInputGraph(g, layoutGraph));
    });
  }
  function runLayout(g, time2) {
    time2("    makeSpaceForEdgeLabels", () => makeSpaceForEdgeLabels(g));
    time2("    removeSelfEdges", () => removeSelfEdges(g));
    time2("    acyclic", () => run(g));
    time2("    nestingGraph.run", () => run3(g));
    time2("    rank", () => rank(asNonCompoundGraph(g)));
    time2("    injectEdgeLabelProxies", () => injectEdgeLabelProxies(g));
    time2("    removeEmptyRanks", () => removeEmptyRanks(g));
    time2("    nestingGraph.cleanup", () => cleanup(g));
    time2("    normalizeRanks", () => normalizeRanks(g));
    time2("    assignRankMinMax", () => assignRankMinMax(g));
    time2("    removeEdgeLabelProxies", () => removeEdgeLabelProxies(g));
    time2("    normalize.run", () => run2(g));
    time2("    parentDummyChains", () => parentDummyChains(g));
    time2("    addBorderSegments", () => addBorderSegments(g));
    time2("    order", () => order(g));
    time2("    insertSelfEdges", () => insertSelfEdges(g));
    time2("    adjustCoordinateSystem", () => adjust(g));
    time2("    position", () => position(g));
    time2("    positionSelfEdges", () => positionSelfEdges(g));
    time2("    removeBorderNodes", () => removeBorderNodes(g));
    time2("    normalize.undo", () => undo3(g));
    time2("    fixupEdgeLabelCoords", () => fixupEdgeLabelCoords(g));
    time2("    undoCoordinateSystem", () => undo2(g));
    time2("    translateGraph", () => translateGraph(g));
    time2("    assignNodeIntersects", () => assignNodeIntersects(g));
    time2("    reversePoints", () => reversePointsForReversedEdges(g));
    time2("    acyclic.undo", () => undo(g));
  }
  function updateInputGraph(inputGraph, layoutGraph) {
    forEach_default(inputGraph.nodes(), function(v) {
      var inputLabel = inputGraph.node(v);
      var layoutLabel = layoutGraph.node(v);
      if (inputLabel) {
        inputLabel.x = layoutLabel.x;
        inputLabel.y = layoutLabel.y;
        if (layoutGraph.children(v).length) {
          inputLabel.width = layoutLabel.width;
          inputLabel.height = layoutLabel.height;
        }
      }
    });
    forEach_default(inputGraph.edges(), function(e) {
      var inputLabel = inputGraph.edge(e);
      var layoutLabel = layoutGraph.edge(e);
      inputLabel.points = layoutLabel.points;
      if (Object.prototype.hasOwnProperty.call(layoutLabel, "x")) {
        inputLabel.x = layoutLabel.x;
        inputLabel.y = layoutLabel.y;
      }
    });
    inputGraph.graph().width = layoutGraph.graph().width;
    inputGraph.graph().height = layoutGraph.graph().height;
  }
  var graphNumAttrs = ["nodesep", "edgesep", "ranksep", "marginx", "marginy"];
  var graphDefaults = { ranksep: 50, edgesep: 20, nodesep: 50, rankdir: "tb" };
  var graphAttrs = ["acyclicer", "ranker", "rankdir", "align"];
  var nodeNumAttrs = ["width", "height"];
  var nodeDefaults = { width: 0, height: 0 };
  var edgeNumAttrs = ["minlen", "weight", "width", "height", "labeloffset"];
  var edgeDefaults = {
    minlen: 1,
    weight: 1,
    width: 0,
    height: 0,
    labeloffset: 10,
    labelpos: "r"
  };
  var edgeAttrs = ["labelpos"];
  function buildLayoutGraph(inputGraph) {
    var g = new Graph({ multigraph: true, compound: true });
    var graph = canonicalize(inputGraph.graph());
    g.setGraph(
      merge_default({}, graphDefaults, selectNumberAttrs(graph, graphNumAttrs), pick_default(graph, graphAttrs))
    );
    forEach_default(inputGraph.nodes(), function(v) {
      var node = canonicalize(inputGraph.node(v));
      g.setNode(v, defaults_default(selectNumberAttrs(node, nodeNumAttrs), nodeDefaults));
      g.setParent(v, inputGraph.parent(v));
    });
    forEach_default(inputGraph.edges(), function(e) {
      var edge = canonicalize(inputGraph.edge(e));
      g.setEdge(
        e,
        merge_default({}, edgeDefaults, selectNumberAttrs(edge, edgeNumAttrs), pick_default(edge, edgeAttrs))
      );
    });
    return g;
  }
  function makeSpaceForEdgeLabels(g) {
    var graph = g.graph();
    graph.ranksep /= 2;
    forEach_default(g.edges(), function(e) {
      var edge = g.edge(e);
      edge.minlen *= 2;
      if (edge.labelpos.toLowerCase() !== "c") {
        if (graph.rankdir === "TB" || graph.rankdir === "BT") {
          edge.width += edge.labeloffset;
        } else {
          edge.height += edge.labeloffset;
        }
      }
    });
  }
  function injectEdgeLabelProxies(g) {
    forEach_default(g.edges(), function(e) {
      var edge = g.edge(e);
      if (edge.width && edge.height) {
        var v = g.node(e.v);
        var w = g.node(e.w);
        var label = { rank: (w.rank - v.rank) / 2 + v.rank, e };
        addDummyNode(g, "edge-proxy", label, "_ep");
      }
    });
  }
  function assignRankMinMax(g) {
    var maxRank2 = 0;
    forEach_default(g.nodes(), function(v) {
      var node = g.node(v);
      if (node.borderTop) {
        node.minRank = g.node(node.borderTop).rank;
        node.maxRank = g.node(node.borderBottom).rank;
        maxRank2 = max_default(maxRank2, node.maxRank);
      }
    });
    g.graph().maxRank = maxRank2;
  }
  function removeEdgeLabelProxies(g) {
    forEach_default(g.nodes(), function(v) {
      var node = g.node(v);
      if (node.dummy === "edge-proxy") {
        g.edge(node.e).labelRank = node.rank;
        g.removeNode(v);
      }
    });
  }
  function translateGraph(g) {
    var minX = Number.POSITIVE_INFINITY;
    var maxX = 0;
    var minY = Number.POSITIVE_INFINITY;
    var maxY = 0;
    var graphLabel = g.graph();
    var marginX = graphLabel.marginx || 0;
    var marginY = graphLabel.marginy || 0;
    function getExtremes(attrs) {
      var x = attrs.x;
      var y = attrs.y;
      var w = attrs.width;
      var h = attrs.height;
      minX = Math.min(minX, x - w / 2);
      maxX = Math.max(maxX, x + w / 2);
      minY = Math.min(minY, y - h / 2);
      maxY = Math.max(maxY, y + h / 2);
    }
    forEach_default(g.nodes(), function(v) {
      getExtremes(g.node(v));
    });
    forEach_default(g.edges(), function(e) {
      var edge = g.edge(e);
      if (Object.prototype.hasOwnProperty.call(edge, "x")) {
        getExtremes(edge);
      }
    });
    minX -= marginX;
    minY -= marginY;
    forEach_default(g.nodes(), function(v) {
      var node = g.node(v);
      node.x -= minX;
      node.y -= minY;
    });
    forEach_default(g.edges(), function(e) {
      var edge = g.edge(e);
      forEach_default(edge.points, function(p) {
        p.x -= minX;
        p.y -= minY;
      });
      if (Object.prototype.hasOwnProperty.call(edge, "x")) {
        edge.x -= minX;
      }
      if (Object.prototype.hasOwnProperty.call(edge, "y")) {
        edge.y -= minY;
      }
    });
    graphLabel.width = maxX - minX + marginX;
    graphLabel.height = maxY - minY + marginY;
  }
  function assignNodeIntersects(g) {
    forEach_default(g.edges(), function(e) {
      var edge = g.edge(e);
      var nodeV = g.node(e.v);
      var nodeW = g.node(e.w);
      var p1, p2;
      if (!edge.points) {
        edge.points = [];
        p1 = nodeW;
        p2 = nodeV;
      } else {
        p1 = edge.points[0];
        p2 = edge.points[edge.points.length - 1];
      }
      edge.points.unshift(intersectRect(nodeV, p1));
      edge.points.push(intersectRect(nodeW, p2));
    });
  }
  function fixupEdgeLabelCoords(g) {
    forEach_default(g.edges(), function(e) {
      var edge = g.edge(e);
      if (Object.prototype.hasOwnProperty.call(edge, "x")) {
        if (edge.labelpos === "l" || edge.labelpos === "r") {
          edge.width -= edge.labeloffset;
        }
        switch (edge.labelpos) {
          case "l":
            edge.x -= edge.width / 2 + edge.labeloffset;
            break;
          case "r":
            edge.x += edge.width / 2 + edge.labeloffset;
            break;
        }
      }
    });
  }
  function reversePointsForReversedEdges(g) {
    forEach_default(g.edges(), function(e) {
      var edge = g.edge(e);
      if (edge.reversed) {
        edge.points.reverse();
      }
    });
  }
  function removeBorderNodes(g) {
    forEach_default(g.nodes(), function(v) {
      if (g.children(v).length) {
        var node = g.node(v);
        var t = g.node(node.borderTop);
        var b = g.node(node.borderBottom);
        var l = g.node(last_default(node.borderLeft));
        var r = g.node(last_default(node.borderRight));
        node.width = Math.abs(r.x - l.x);
        node.height = Math.abs(b.y - t.y);
        node.x = l.x + node.width / 2;
        node.y = t.y + node.height / 2;
      }
    });
    forEach_default(g.nodes(), function(v) {
      if (g.node(v).dummy === "border") {
        g.removeNode(v);
      }
    });
  }
  function removeSelfEdges(g) {
    forEach_default(g.edges(), function(e) {
      if (e.v === e.w) {
        var node = g.node(e.v);
        if (!node.selfEdges) {
          node.selfEdges = [];
        }
        node.selfEdges.push({ e, label: g.edge(e) });
        g.removeEdge(e);
      }
    });
  }
  function insertSelfEdges(g) {
    var layers = buildLayerMatrix(g);
    forEach_default(layers, function(layer) {
      var orderShift = 0;
      forEach_default(layer, function(v, i) {
        var node = g.node(v);
        node.order = i + orderShift;
        forEach_default(node.selfEdges, function(selfEdge) {
          addDummyNode(
            g,
            "selfedge",
            {
              width: selfEdge.label.width,
              height: selfEdge.label.height,
              rank: node.rank,
              order: i + ++orderShift,
              e: selfEdge.e,
              label: selfEdge.label
            },
            "_se"
          );
        });
        delete node.selfEdges;
      });
    });
  }
  function positionSelfEdges(g) {
    forEach_default(g.nodes(), function(v) {
      var node = g.node(v);
      if (node.dummy === "selfedge") {
        var selfNode = g.node(node.e.v);
        var x = selfNode.x + selfNode.width / 2;
        var y = selfNode.y;
        var dx = node.x - x;
        var dy = selfNode.height / 2;
        g.setEdge(node.e, node.label);
        g.removeNode(v);
        node.label.points = [
          { x: x + 2 * dx / 3, y: y - dy },
          { x: x + 5 * dx / 6, y: y - dy },
          { x: x + dx, y },
          { x: x + 5 * dx / 6, y: y + dy },
          { x: x + 2 * dx / 3, y: y + dy }
        ];
        node.label.x = node.x;
        node.label.y = node.y;
      }
    });
  }
  function selectNumberAttrs(obj, attrs) {
    return mapValues_default(pick_default(obj, attrs), Number);
  }
  function canonicalize(attrs) {
    var newAttrs = {};
    forEach_default(attrs, function(v, k) {
      newAttrs[k.toLowerCase()] = v;
    });
    return newAttrs;
  }

  // node_modules/dagre-d3-es/src/dagre-js/util.js
  function isSubgraph(g, v) {
    return !!g.children(v).length;
  }
  function edgeToId(e) {
    return escapeId(e.v) + ":" + escapeId(e.w) + ":" + escapeId(e.name);
  }
  var ID_DELIM = /:/g;
  function escapeId(str) {
    return str ? String(str).replace(ID_DELIM, "\\:") : "";
  }
  function applyStyle(dom, styleFn) {
    if (styleFn) {
      dom.attr("style", styleFn);
    }
  }
  function applyClass(dom, classFn, otherClasses) {
    if (classFn) {
      dom.attr("class", classFn).attr("class", otherClasses + " " + dom.attr("class"));
    }
  }
  function applyTransition(selection, g) {
    var graph = g.graph();
    if (isPlainObject_default(graph)) {
      var transition = graph.transition;
      if (isFunction_default(transition)) {
        return transition(selection);
      }
    }
    return selection;
  }

  // node_modules/dagre-d3-es/src/dagre-js/arrows.js
  var arrows = {
    normal,
    vee,
    undirected
  };
  function setArrows(value) {
    arrows = value;
  }
  function normal(parent, id, edge, type) {
    var marker = parent.append("marker").attr("id", id).attr("viewBox", "0 0 10 10").attr("refX", 9).attr("refY", 5).attr("markerUnits", "strokeWidth").attr("markerWidth", 8).attr("markerHeight", 6).attr("orient", "auto");
    var path = marker.append("path").attr("d", "M 0 0 L 10 5 L 0 10 z").style("stroke-width", 1).style("stroke-dasharray", "1,0");
    applyStyle(path, edge[type + "Style"]);
    if (edge[type + "Class"]) {
      path.attr("class", edge[type + "Class"]);
    }
  }
  function vee(parent, id, edge, type) {
    var marker = parent.append("marker").attr("id", id).attr("viewBox", "0 0 10 10").attr("refX", 9).attr("refY", 5).attr("markerUnits", "strokeWidth").attr("markerWidth", 8).attr("markerHeight", 6).attr("orient", "auto");
    var path = marker.append("path").attr("d", "M 0 0 L 10 5 L 0 10 L 4 5 z").style("stroke-width", 1).style("stroke-dasharray", "1,0");
    applyStyle(path, edge[type + "Style"]);
    if (edge[type + "Class"]) {
      path.attr("class", edge[type + "Class"]);
    }
  }
  function undirected(parent, id, edge, type) {
    var marker = parent.append("marker").attr("id", id).attr("viewBox", "0 0 10 10").attr("refX", 9).attr("refY", 5).attr("markerUnits", "strokeWidth").attr("markerWidth", 8).attr("markerHeight", 6).attr("orient", "auto");
    var path = marker.append("path").attr("d", "M 0 5 L 10 5").style("stroke-width", 1).style("stroke-dasharray", "1,0");
    applyStyle(path, edge[type + "Style"]);
    if (edge[type + "Class"]) {
      path.attr("class", edge[type + "Class"]);
    }
  }

  // node_modules/dagre-d3-es/src/dagre-js/create-clusters.js
  var d3 = __toESM(require_d3_global_shim(), 1);

  // node_modules/dagre-d3-es/src/dagre-js/label/add-html-label.js
  function addHtmlLabel(root2, node) {
    var fo = root2.append("foreignObject").attr("width", "100000");
    var div = fo.append("xhtml:div");
    div.attr("xmlns", "http://www.w3.org/1999/xhtml");
    var label = node.label;
    switch (typeof label) {
      case "function":
        div.insert(label);
        break;
      case "object":
        div.insert(function() {
          return label;
        });
        break;
      default:
        div.html(label);
    }
    applyStyle(div, node.labelStyle);
    div.style("display", "inline-block");
    div.style("white-space", "nowrap");
    var client = div.node();
    fo.attr("width", client.offsetWidth).attr("height", client.offsetHeight);
    return fo;
  }

  // node_modules/dagre-d3-es/src/dagre-js/label/add-svg-label.js
  function addSVGLabel(root2, node) {
    var domNode = root2;
    domNode.node().appendChild(node.label);
    applyStyle(domNode, node.labelStyle);
    return domNode;
  }

  // node_modules/dagre-d3-es/src/dagre-js/label/add-text-label.js
  function addTextLabel(root2, node) {
    var domNode = root2.append("text");
    var lines = processEscapeSequences(node.label).split("\n");
    for (var i = 0; i < lines.length; i++) {
      domNode.append("tspan").attr("xml:space", "preserve").attr("dy", "1em").attr("x", "1").text(lines[i]);
    }
    applyStyle(domNode, node.labelStyle);
    return domNode;
  }
  function processEscapeSequences(text) {
    var newText = "";
    var escaped = false;
    var ch;
    for (var i = 0; i < text.length; ++i) {
      ch = text[i];
      if (escaped) {
        switch (ch) {
          case "n":
            newText += "\n";
            break;
          default:
            newText += ch;
        }
        escaped = false;
      } else if (ch === "\\") {
        escaped = true;
      } else {
        newText += ch;
      }
    }
    return newText;
  }

  // node_modules/dagre-d3-es/src/dagre-js/label/add-label.js
  function addLabel(root2, node, location2) {
    var label = node.label;
    var labelSvg = root2.append("g");
    if (node.labelType === "svg") {
      addSVGLabel(labelSvg, node);
    } else if (typeof label !== "string" || node.labelType === "html") {
      addHtmlLabel(labelSvg, node);
    } else {
      addTextLabel(labelSvg, node);
    }
    var labelBBox = labelSvg.node().getBBox();
    var y;
    switch (location2) {
      case "top":
        y = -node.height / 2;
        break;
      case "bottom":
        y = node.height / 2 - labelBBox.height;
        break;
      default:
        y = -labelBBox.height / 2;
    }
    labelSvg.attr("transform", "translate(" + -labelBBox.width / 2 + "," + y + ")");
    return labelSvg;
  }

  // node_modules/dagre-d3-es/src/dagre-js/create-clusters.js
  var createClusters = function(selection, g) {
    var clusters = g.nodes().filter(function(v) {
      return isSubgraph(g, v);
    });
    var svgClusters = selection.selectAll("g.cluster").data(clusters, function(v) {
      return v;
    });
    applyTransition(svgClusters.exit(), g).style("opacity", 0).remove();
    var enterSelection = svgClusters.enter().append("g").attr("class", "cluster").attr("id", function(v) {
      var node = g.node(v);
      return node.id;
    }).style("opacity", 0).each(function(v) {
      var node = g.node(v);
      var thisGroup = d3.select(this);
      d3.select(this).append("rect");
      var labelGroup = thisGroup.append("g").attr("class", "label");
      addLabel(labelGroup, node, node.clusterLabelPos);
    });
    svgClusters = svgClusters.merge(enterSelection);
    svgClusters = applyTransition(svgClusters, g).style("opacity", 1);
    svgClusters.selectAll("rect").each(function(c) {
      var node = g.node(c);
      var domCluster = d3.select(this);
      applyStyle(domCluster, node.style);
    });
    return svgClusters;
  };
  function setCreateClusters(value) {
    createClusters = value;
  }

  // node_modules/dagre-d3-es/src/dagre-js/create-edge-labels.js
  var d32 = __toESM(require_d3_global_shim(), 1);
  var createEdgeLabels = function(selection, g) {
    var svgEdgeLabels = selection.selectAll("g.edgeLabel").data(g.edges(), function(e) {
      return edgeToId(e);
    }).classed("update", true);
    svgEdgeLabels.exit().remove();
    svgEdgeLabels.enter().append("g").classed("edgeLabel", true).style("opacity", 0);
    svgEdgeLabels = selection.selectAll("g.edgeLabel");
    svgEdgeLabels.each(function(e) {
      var root2 = d32.select(this);
      root2.select(".label").remove();
      var edge = g.edge(e);
      var label = addLabel(root2, g.edge(e), 0).classed("label", true);
      var bbox = label.node().getBBox();
      if (edge.labelId) {
        label.attr("id", edge.labelId);
      }
      if (!Object.prototype.hasOwnProperty.call(edge, "width")) {
        edge.width = bbox.width;
      }
      if (!Object.prototype.hasOwnProperty.call(edge, "height")) {
        edge.height = bbox.height;
      }
    });
    var exitSelection;
    if (svgEdgeLabels.exit) {
      exitSelection = svgEdgeLabels.exit();
    } else {
      exitSelection = svgEdgeLabels.selectAll(null);
    }
    applyTransition(exitSelection, g).style("opacity", 0).remove();
    return svgEdgeLabels;
  };
  function setCreateEdgeLabels(value) {
    createEdgeLabels = value;
  }

  // node_modules/dagre-d3-es/src/dagre-js/create-edge-paths.js
  var d33 = __toESM(require_d3_global_shim(), 1);

  // node_modules/dagre-d3-es/src/dagre-js/intersect/intersect-node.js
  var intersect_node_exports = {};
  __export(intersect_node_exports, {
    intersectNode: () => intersectNode
  });
  function intersectNode(node, point) {
    return node.intersect(point);
  }

  // node_modules/dagre-d3-es/src/dagre-js/create-edge-paths.js
  var createEdgePaths = function(selection, g, arrows2) {
    var previousPaths = selection.selectAll("g.edgePath").data(g.edges(), function(e) {
      return edgeToId(e);
    }).classed("update", true);
    var newPaths = enter(previousPaths, g);
    exit(previousPaths, g);
    var svgPaths = previousPaths.merge !== void 0 ? previousPaths.merge(newPaths) : previousPaths;
    applyTransition(svgPaths, g).style("opacity", 1);
    svgPaths.each(function(e) {
      var domEdge = d33.select(this);
      var edge = g.edge(e);
      edge.elem = this;
      if (edge.id) {
        domEdge.attr("id", edge.id);
      }
      applyClass(
        domEdge,
        edge["class"],
        (domEdge.classed("update") ? "update " : "") + "edgePath"
      );
    });
    svgPaths.selectAll("path.path").each(function(e) {
      var edge = g.edge(e);
      edge.arrowheadId = uniqueId_default("arrowhead");
      var domEdge = d33.select(this).attr("marker-end", function() {
        return "url(" + makeFragmentRef(location.href, edge.arrowheadId) + ")";
      }).style("fill", "none");
      applyTransition(domEdge, g).attr("d", function(e2) {
        return calcPoints(g, e2);
      });
      applyStyle(domEdge, edge.style);
    });
    svgPaths.selectAll("defs *").remove();
    svgPaths.selectAll("defs").each(function(e) {
      var edge = g.edge(e);
      var arrowhead = arrows2[edge.arrowhead];
      arrowhead(d33.select(this), edge.arrowheadId, edge, "arrowhead");
    });
    return svgPaths;
  };
  function setCreateEdgePaths(value) {
    createEdgePaths = value;
  }
  function makeFragmentRef(url, fragmentId) {
    var baseUrl = url.split("#")[0];
    return baseUrl + "#" + fragmentId;
  }
  function calcPoints(g, e) {
    var edge = g.edge(e);
    var tail = g.node(e.v);
    var head = g.node(e.w);
    var points = edge.points.slice(1, edge.points.length - 1);
    points.unshift(intersectNode(tail, points[0]));
    points.push(intersectNode(head, points[points.length - 1]));
    return createLine(edge, points);
  }
  function createLine(edge, points) {
    var line2 = (d33.line || d33.svg.line)().x(function(d) {
      return d.x;
    }).y(function(d) {
      return d.y;
    });
    (line2.curve || line2.interpolate)(edge.curve);
    return line2(points);
  }
  function getCoords(elem) {
    var bbox = elem.getBBox();
    var matrix = elem.ownerSVGElement.getScreenCTM().inverse().multiply(elem.getScreenCTM()).translate(bbox.width / 2, bbox.height / 2);
    return { x: matrix.e, y: matrix.f };
  }
  function enter(svgPaths, g) {
    var svgPathsEnter = svgPaths.enter().append("g").attr("class", "edgePath").style("opacity", 0);
    svgPathsEnter.append("path").attr("class", "path").attr("d", function(e) {
      var edge = g.edge(e);
      var sourceElem = g.node(e.v).elem;
      var points = range_default(edge.points.length).map(function() {
        return getCoords(sourceElem);
      });
      return createLine(edge, points);
    });
    svgPathsEnter.append("defs");
    return svgPathsEnter;
  }
  function exit(svgPaths, g) {
    var svgPathExit = svgPaths.exit();
    applyTransition(svgPathExit, g).style("opacity", 0).remove();
  }

  // node_modules/dagre-d3-es/src/dagre-js/create-nodes.js
  var d34 = __toESM(require_d3_global_shim(), 1);
  var createNodes = function(selection, g, shapes2) {
    var simpleNodes = g.nodes().filter(function(v) {
      return !isSubgraph(g, v);
    });
    var svgNodes = selection.selectAll("g.node").data(simpleNodes, function(v) {
      return v;
    }).classed("update", true);
    svgNodes.exit().remove();
    svgNodes.enter().append("g").attr("class", "node").style("opacity", 0);
    svgNodes = selection.selectAll("g.node");
    svgNodes.each(function(v) {
      var node = g.node(v);
      var thisGroup = d34.select(this);
      applyClass(
        thisGroup,
        node["class"],
        (thisGroup.classed("update") ? "update " : "") + "node"
      );
      thisGroup.select("g.label").remove();
      var labelGroup = thisGroup.append("g").attr("class", "label");
      var labelDom = addLabel(labelGroup, node);
      var shape = shapes2[node.shape];
      var bbox = pick_default(labelDom.node().getBBox(), "width", "height");
      node.elem = this;
      if (node.id) {
        thisGroup.attr("id", node.id);
      }
      if (node.labelId) {
        labelGroup.attr("id", node.labelId);
      }
      if (Object.prototype.hasOwnProperty.call(node, "width")) {
        bbox.width = node.width;
      }
      if (Object.prototype.hasOwnProperty.call(node, "height")) {
        bbox.height = node.height;
      }
      bbox.width += node.paddingLeft + node.paddingRight;
      bbox.height += node.paddingTop + node.paddingBottom;
      labelGroup.attr(
        "transform",
        "translate(" + (node.paddingLeft - node.paddingRight) / 2 + "," + (node.paddingTop - node.paddingBottom) / 2 + ")"
      );
      var root2 = d34.select(this);
      root2.select(".label-container").remove();
      var shapeSvg = shape(root2, bbox, node).classed("label-container", true);
      applyStyle(shapeSvg, node.style);
      var shapeBBox = shapeSvg.node().getBBox();
      node.width = shapeBBox.width;
      node.height = shapeBBox.height;
    });
    var exitSelection;
    if (svgNodes.exit) {
      exitSelection = svgNodes.exit();
    } else {
      exitSelection = svgNodes.selectAll(null);
    }
    applyTransition(exitSelection, g).style("opacity", 0).remove();
    return svgNodes;
  };
  function setCreateNodes(value) {
    createNodes = value;
  }

  // node_modules/dagre-d3-es/src/dagre-js/position-clusters.js
  var d35 = __toESM(require_d3_global_shim(), 1);
  function positionClusters(selection, g) {
    var created = selection.filter(function() {
      return !d35.select(this).classed("update");
    });
    function translate(v) {
      var node = g.node(v);
      return "translate(" + node.x + "," + node.y + ")";
    }
    created.attr("transform", translate);
    applyTransition(selection, g).style("opacity", 1).attr("transform", translate);
    applyTransition(created.selectAll("rect"), g).attr("width", function(v) {
      return g.node(v).width;
    }).attr("height", function(v) {
      return g.node(v).height;
    }).attr("x", function(v) {
      var node = g.node(v);
      return -node.width / 2;
    }).attr("y", function(v) {
      var node = g.node(v);
      return -node.height / 2;
    });
  }

  // node_modules/dagre-d3-es/src/dagre-js/position-edge-labels.js
  var d36 = __toESM(require_d3_global_shim(), 1);
  function positionEdgeLabels(selection, g) {
    var created = selection.filter(function() {
      return !d36.select(this).classed("update");
    });
    function translate(e) {
      var edge = g.edge(e);
      return Object.prototype.hasOwnProperty.call(edge, "x") ? "translate(" + edge.x + "," + edge.y + ")" : "";
    }
    created.attr("transform", translate);
    applyTransition(selection, g).style("opacity", 1).attr("transform", translate);
  }

  // node_modules/dagre-d3-es/src/dagre-js/position-nodes.js
  var d37 = __toESM(require_d3_global_shim(), 1);
  function positionNodes(selection, g) {
    var created = selection.filter(function() {
      return !d37.select(this).classed("update");
    });
    function translate(v) {
      var node = g.node(v);
      return "translate(" + node.x + "," + node.y + ")";
    }
    created.attr("transform", translate);
    applyTransition(selection, g).style("opacity", 1).attr("transform", translate);
  }

  // node_modules/dagre-d3-es/src/dagre-js/intersect/intersect-circle.js
  var intersect_circle_exports = {};
  __export(intersect_circle_exports, {
    intersectCircle: () => intersectCircle
  });

  // node_modules/dagre-d3-es/src/dagre-js/intersect/intersect-ellipse.js
  var intersect_ellipse_exports = {};
  __export(intersect_ellipse_exports, {
    intersectEllipse: () => intersectEllipse
  });
  function intersectEllipse(node, rx, ry, point) {
    var cx = node.x;
    var cy = node.y;
    var px = cx - point.x;
    var py = cy - point.y;
    var det = Math.sqrt(rx * rx * py * py + ry * ry * px * px);
    var dx = Math.abs(rx * ry * px / det);
    if (point.x < cx) {
      dx = -dx;
    }
    var dy = Math.abs(rx * ry * py / det);
    if (point.y < cy) {
      dy = -dy;
    }
    return { x: cx + dx, y: cy + dy };
  }

  // node_modules/dagre-d3-es/src/dagre-js/intersect/intersect-circle.js
  function intersectCircle(node, rx, point) {
    return intersectEllipse(node, rx, rx, point);
  }

  // node_modules/dagre-d3-es/src/dagre-js/intersect/intersect-polygon.js
  var intersect_polygon_exports = {};
  __export(intersect_polygon_exports, {
    intersectPolygon: () => intersectPolygon
  });

  // node_modules/dagre-d3-es/src/dagre-js/intersect/intersect-line.js
  function intersectLine(p1, p2, q1, q2) {
    var a1, a2, b1, b2, c1, c2;
    var r1, r2, r3, r4;
    var denom, offset, num;
    var x, y;
    a1 = p2.y - p1.y;
    b1 = p1.x - p2.x;
    c1 = p2.x * p1.y - p1.x * p2.y;
    r3 = a1 * q1.x + b1 * q1.y + c1;
    r4 = a1 * q2.x + b1 * q2.y + c1;
    if (r3 !== 0 && r4 !== 0 && sameSign(r3, r4)) {
      return;
    }
    a2 = q2.y - q1.y;
    b2 = q1.x - q2.x;
    c2 = q2.x * q1.y - q1.x * q2.y;
    r1 = a2 * p1.x + b2 * p1.y + c2;
    r2 = a2 * p2.x + b2 * p2.y + c2;
    if (r1 !== 0 && r2 !== 0 && sameSign(r1, r2)) {
      return;
    }
    denom = a1 * b2 - a2 * b1;
    if (denom === 0) {
      return;
    }
    offset = Math.abs(denom / 2);
    num = b1 * c2 - b2 * c1;
    x = num < 0 ? (num - offset) / denom : (num + offset) / denom;
    num = a2 * c1 - a1 * c2;
    y = num < 0 ? (num - offset) / denom : (num + offset) / denom;
    return { x, y };
  }
  function sameSign(r1, r2) {
    return r1 * r2 > 0;
  }

  // node_modules/dagre-d3-es/src/dagre-js/intersect/intersect-polygon.js
  function intersectPolygon(node, polyPoints, point) {
    var x1 = node.x;
    var y1 = node.y;
    var intersections = [];
    var minX = Number.POSITIVE_INFINITY;
    var minY = Number.POSITIVE_INFINITY;
    polyPoints.forEach(function(entry) {
      minX = Math.min(minX, entry.x);
      minY = Math.min(minY, entry.y);
    });
    var left = x1 - node.width / 2 - minX;
    var top = y1 - node.height / 2 - minY;
    for (var i = 0; i < polyPoints.length; i++) {
      var p1 = polyPoints[i];
      var p2 = polyPoints[i < polyPoints.length - 1 ? i + 1 : 0];
      var intersect = intersectLine(
        node,
        point,
        { x: left + p1.x, y: top + p1.y },
        { x: left + p2.x, y: top + p2.y }
      );
      if (intersect) {
        intersections.push(intersect);
      }
    }
    if (!intersections.length) {
      console.log("NO INTERSECTION FOUND, RETURN NODE CENTER", node);
      return node;
    }
    if (intersections.length > 1) {
      intersections.sort(function(p, q) {
        var pdx = p.x - point.x;
        var pdy = p.y - point.y;
        var distp = Math.sqrt(pdx * pdx + pdy * pdy);
        var qdx = q.x - point.x;
        var qdy = q.y - point.y;
        var distq = Math.sqrt(qdx * qdx + qdy * qdy);
        return distp < distq ? -1 : distp === distq ? 0 : 1;
      });
    }
    return intersections[0];
  }

  // node_modules/dagre-d3-es/src/dagre-js/intersect/intersect-rect.js
  var intersect_rect_exports = {};
  __export(intersect_rect_exports, {
    intersectRect: () => intersectRect2
  });
  function intersectRect2(node, point) {
    var x = node.x;
    var y = node.y;
    var dx = point.x - x;
    var dy = point.y - y;
    var w = node.width / 2;
    var h = node.height / 2;
    var sx, sy;
    if (Math.abs(dy) * w > Math.abs(dx) * h) {
      if (dy < 0) {
        h = -h;
      }
      sx = dy === 0 ? 0 : h * dx / dy;
      sy = h;
    } else {
      if (dx < 0) {
        w = -w;
      }
      sx = w;
      sy = dx === 0 ? 0 : w * dy / dx;
    }
    return { x: x + sx, y: y + sy };
  }

  // node_modules/dagre-d3-es/src/dagre-js/shapes.js
  var shapes = {
    rect,
    ellipse,
    circle,
    diamond
  };
  function setShapes(value) {
    shapes = value;
  }
  function rect(parent, bbox, node) {
    var shapeSvg = parent.insert("rect", ":first-child").attr("rx", node.rx).attr("ry", node.ry).attr("x", -bbox.width / 2).attr("y", -bbox.height / 2).attr("width", bbox.width).attr("height", bbox.height);
    node.intersect = function(point) {
      return intersectRect2(node, point);
    };
    return shapeSvg;
  }
  function ellipse(parent, bbox, node) {
    var rx = bbox.width / 2;
    var ry = bbox.height / 2;
    var shapeSvg = parent.insert("ellipse", ":first-child").attr("x", -bbox.width / 2).attr("y", -bbox.height / 2).attr("rx", rx).attr("ry", ry);
    node.intersect = function(point) {
      return intersectEllipse(node, rx, ry, point);
    };
    return shapeSvg;
  }
  function circle(parent, bbox, node) {
    var r = Math.max(bbox.width, bbox.height) / 2;
    var shapeSvg = parent.insert("circle", ":first-child").attr("x", -bbox.width / 2).attr("y", -bbox.height / 2).attr("r", r);
    node.intersect = function(point) {
      return intersectCircle(node, r, point);
    };
    return shapeSvg;
  }
  function diamond(parent, bbox, node) {
    var w = bbox.width * Math.SQRT2 / 2;
    var h = bbox.height * Math.SQRT2 / 2;
    var points = [
      { x: 0, y: -h },
      { x: -w, y: 0 },
      { x: 0, y: h },
      { x: w, y: 0 }
    ];
    var shapeSvg = parent.insert("polygon", ":first-child").attr(
      "points",
      points.map(function(p) {
        return p.x + "," + p.y;
      }).join(" ")
    );
    node.intersect = function(p) {
      return intersectPolygon(node, points, p);
    };
    return shapeSvg;
  }

  // node_modules/dagre-d3-es/src/dagre-js/render.js
  function render() {
    var fn = function(svg2, g) {
      preProcessGraph(g);
      var outputGroup = createOrSelectGroup(svg2, "output");
      var clustersGroup = createOrSelectGroup(outputGroup, "clusters");
      var edgePathsGroup = createOrSelectGroup(outputGroup, "edgePaths");
      var edgeLabels = createEdgeLabels(createOrSelectGroup(outputGroup, "edgeLabels"), g);
      var nodes = createNodes(createOrSelectGroup(outputGroup, "nodes"), g, shapes);
      layout(g);
      positionNodes(nodes, g);
      positionEdgeLabels(edgeLabels, g);
      createEdgePaths(edgePathsGroup, g, arrows);
      var clusters = createClusters(clustersGroup, g);
      positionClusters(clusters, g);
      postProcessGraph(g);
    };
    fn.createNodes = function(value) {
      if (!arguments.length) return createNodes;
      setCreateNodes(value);
      return fn;
    };
    fn.createClusters = function(value) {
      if (!arguments.length) return createClusters;
      setCreateClusters(value);
      return fn;
    };
    fn.createEdgeLabels = function(value) {
      if (!arguments.length) return createEdgeLabels;
      setCreateEdgeLabels(value);
      return fn;
    };
    fn.createEdgePaths = function(value) {
      if (!arguments.length) return createEdgePaths;
      setCreateEdgePaths(value);
      return fn;
    };
    fn.shapes = function(value) {
      if (!arguments.length) return shapes;
      setShapes(value);
      return fn;
    };
    fn.arrows = function(value) {
      if (!arguments.length) return arrows;
      setArrows(value);
      return fn;
    };
    return fn;
  }
  var NODE_DEFAULT_ATTRS = {
    paddingLeft: 10,
    paddingRight: 10,
    paddingTop: 10,
    paddingBottom: 10,
    rx: 0,
    ry: 0,
    shape: "rect"
  };
  var EDGE_DEFAULT_ATTRS = {
    arrowhead: "normal",
    curve: d38.curveLinear
  };
  function preProcessGraph(g) {
    g.nodes().forEach((v) => {
      const node = g.node(v);
      if (!Object.prototype.hasOwnProperty.call(node, "label") && !g.children(v).length) {
        node.label = v;
      }
      if (Object.prototype.hasOwnProperty.call(node, "paddingX")) {
        defaults_default(node, {
          paddingLeft: node.paddingX,
          paddingRight: node.paddingX
        });
      }
      if (Object.prototype.hasOwnProperty.call(node, "paddingY")) {
        defaults_default(node, {
          paddingTop: node.paddingY,
          paddingBottom: node.paddingY
        });
      }
      if (Object.prototype.hasOwnProperty.call(node, "padding")) {
        defaults_default(node, {
          paddingLeft: node.padding,
          paddingRight: node.padding,
          paddingTop: node.padding,
          paddingBottom: node.padding
        });
      }
      defaults_default(node, NODE_DEFAULT_ATTRS);
      ["paddingLeft", "paddingRight", "paddingTop", "paddingBottom"].forEach((k) => {
        node[k] = Number(node[k]);
      });
      if (Object.prototype.hasOwnProperty.call(node, "width")) {
        node._prevWidth = node.width;
      }
      if (Object.prototype.hasOwnProperty.call(node, "height")) {
        node._prevHeight = node.height;
      }
    });
    g.edges().forEach(function(e) {
      var edge = g.edge(e);
      if (!Object.prototype.hasOwnProperty.call(edge, "label")) {
        edge.label = "";
      }
      defaults_default(edge, EDGE_DEFAULT_ATTRS);
    });
  }
  function postProcessGraph(g) {
    g.nodes().forEach((v) => {
      var node = g.node(v);
      if (Object.prototype.hasOwnProperty.call(node, "_prevWidth")) {
        node.width = node._prevWidth;
      } else {
        delete node.width;
      }
      if (Object.prototype.hasOwnProperty.call(node, "_prevHeight")) {
        node.height = node._prevHeight;
      } else {
        delete node.height;
      }
      delete node._prevWidth;
      delete node._prevHeight;
    });
  }
  function createOrSelectGroup(root2, name) {
    var selection = root2.select("g." + name);
    if (selection.empty()) {
      selection = root2.append("g").attr("class", name);
    }
    return selection;
  }

  // node_modules/dagre-d3-es/src/dagre-js/intersect/index.js
  var intersect_exports = {};
  __export(intersect_exports, {
    circle: () => intersect_circle_exports,
    ellipse: () => intersect_ellipse_exports,
    node: () => intersect_node_exports,
    polygon: () => intersect_polygon_exports,
    rect: () => intersect_rect_exports
  });
  return __toCommonJS(index_exports);
})();
/*! Bundled license information:

lodash-es/lodash.js:
  (**
   * @license
   * Lodash (Custom Build) <https://lodash.com/>
   * Build: `lodash modularize exports="es" --repo lodash/lodash#4.18.1 -o ./`
   * Copyright OpenJS Foundation and other contributors <https://openjsf.org/>
   * Released under MIT license <https://lodash.com/license>
   * Based on Underscore.js 1.8.3 <http://underscorejs.org/LICENSE>
   * Copyright Jeremy Ashkenas, DocumentCloud and Investigative Reporters & Editors
   *)
*/
